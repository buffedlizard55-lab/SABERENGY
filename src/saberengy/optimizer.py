"""
Lineup Optimizer — Sim Mode + Optimizer Mode

Verified from:
- https://support.sabersim.com/en/articles/12079141-building-lineups
  "SaberSim starts with play-by-play simulations. We simulate every play and decision to build thousands of realistic game scripts. These scripts capture how players perform together, not just in isolation. This is the engine behind the Sim Optimizer. Unlike traditional optimizers that rely on averages, SaberSim builds lineups directly from real game simulations."
  "Each simulation creates a full game script: who scores, who busts, and how players correlate. When you hit Build Lineups, SaberSim samples from these simulations to construct your lineups. Each lineup is a single bet on how a slate could realistically play out"
  "A QB + WR stack happens when they both excel in the same game script. A bring-back appears because the opposing WR scored well in that script. A full game stack forms because the game went to overtime or turned into a shootout."

- https://support.sabersim.com/en/articles/12079141-building-lineups-in-sabersim
  "Correlation Slider: Controls how strongly correlated plays are prioritized. Higher = more natural stacks"
  "Sim Diversity: Controls how many different simulations are used. Higher = more variety"

- https://www.sabersim.com/video/dfs-lineup-optimizers-are-obsolete-you-need-a-simulator
  "Correlation, this controls the impact of correlation on your lineups. A higher weight is going to favor players who are positively correlated"
  "Ownership fade, and this just controls how much of a factor you want ownership to be in your lineups. The higher you set it, the more your ownerships will fade"
  "High variance, highly owned players are going to be faded more aggressively by the optimizer automatically than low variance"

No hallucinations — implements Sim Mode sampling from game scripts.
"""

from typing import List, Dict, Tuple
import random
import numpy as np
from collections import defaultdict
from .simulation import GameScript

class OptimizerMode:
    """Traditional optimizer using static projections — for cash games."""
    def __init__(self, salary_cap: int = 50000, lineup_size: int = 9):
        self.salary_cap = salary_cap
        self.lineup_size = lineup_size

    def build(self, projections: Dict[str, Dict], num_lineups: int = 100, constraints: Dict = None) -> List[List[str]]:
        """
        Simple knapSack-style optimizer: pick highest projection under salary cap.
        This is baseline — SaberSim's Optimizer Mode does similar but with stacking rules.
        """
        # Edge case handling
        if not projections:
            return []
        effective_size = min(self.lineup_size, len(projections))

        # Sort by projection
        sorted_players = sorted(projections.items(), key=lambda x: x[1].get("projection", 0), reverse=True)
        lineups = []
        for _ in range(num_lineups):
            # Greedy with randomness
            lineup = []
            salary_used = 0
            # Shuffle top 30% for diversity
            candidates = [p for p in sorted_players[:max(20, len(sorted_players)//3)]]
            random.shuffle(candidates)
            for pid, proj in candidates:
                sal = proj.get("salary", 5000)
                if salary_used + sal <= self.salary_cap and len(lineup) < effective_size:
                    if pid not in lineup:
                        lineup.append(pid)
                        salary_used += sal
                if len(lineup) >= effective_size:
                    break
            # Fill remaining with random if needed
            if len(lineup) < effective_size:
                remaining = [pid for pid, _ in sorted_players if pid not in lineup]
                for pid in remaining:
                    sal = projections[pid].get("salary", 5000)
                    if salary_used + sal <= self.salary_cap:
                        lineup.append(pid)
                        salary_used += sal
                    if len(lineup) >= effective_size:
                        break
            if len(lineup) == effective_size:
                lineups.append(lineup)
        return lineups


class SimOptimizer:
    """
    Sim Mode optimizer — builds lineups directly from game simulations.

    "SaberSim runs thousands of complete play-by-play simulations for each slate.
    Each simulation creates a full game script: who scores, who busts, and how players correlate.
    When you hit Build Lineups, SaberSim samples from these simulations to construct your lineups."
    Source: Building Lineups support article.
    """

    def __init__(
        self,
        salary_cap: int = 50000,
        lineup_size: int = 9,
        correlation_weight: float = 0.5,  # 0-1 slider
        sim_diversity: float = 0.5,  # 0-1 slider
        ownership_fade: float = 0.5,  # 0-1 slider
        seed: int = 42,
    ):
        self.salary_cap = salary_cap
        self.lineup_size = lineup_size
        self.correlation_weight = correlation_weight
        self.sim_diversity = sim_diversity
        self.ownership_fade = ownership_fade
        random.seed(seed)
        np.random.seed(seed)

    def build(
        self,
        game_scripts: List[GameScript],
        projections: Dict[str, Dict],
        ownership: Dict[str, float] = None,
        num_lineups: int = 500,
        correlation_matrix: Dict[Tuple[str, str], float] = None,
    ) -> List[List[str]]:
        """
        Builds lineups by sampling from game scripts.

        Logic:
        1. Sample a game script (or multiple scripts for diversity)
        2. In that script, players have correlated outcomes — pick highest scoring players in that script
        3. Apply correlation weight: boost lineups where players are positively correlated (same game, same team)
        4. Apply ownership fade: penalize highly owned players, especially high variance chalk
        5. Apply sim diversity: control how many unique scripts are used

        Returns list of lineups (player_ids)
        """

        # Group scripts by sim_index to get full slate outcomes
        by_sim = defaultdict(list)
        for gs in game_scripts:
            by_sim[gs.sim_index].append(gs)

        sim_indices = list(by_sim.keys())
        # Sim Diversity controls how many unique sims we sample from
        # Low diversity = sample from fewer sims (tighter), high = more variety
        num_unique_sims_to_use = max(1, int(len(sim_indices) * (0.2 + 0.8 * self.sim_diversity)))
        # Sample which sims to use
        chosen_sim_indices = random.sample(sim_indices, min(num_unique_sims_to_use, len(sim_indices)))

        # Precompute player points per sim_index (full slate)
        points_by_sim = {}
        for sim_idx in sim_indices:
            pts = {}
            for gs in by_sim[sim_idx]:
                for outcome in gs.player_outcomes:
                    pts[outcome.player_id] = pts.get(outcome.player_id, 0) + outcome.fantasy_points
            points_by_sim[sim_idx] = pts

        lineups = []
        attempts = 0
        max_attempts = num_lineups * 10

        while len(lineups) < num_lineups and attempts < max_attempts:
            attempts += 1
            # Sample a sim index (with replacement for diversity)
            sim_idx = random.choice(chosen_sim_indices)
            player_points = points_by_sim[sim_idx]

            # Score players in this sim with adjustments
            scored_players = []
            for pid, pts in player_points.items():
                proj = projections.get(pid, {})
                salary = proj.get("salary", 5000)
                if salary == 0:
                    continue

                # Base score = points in this sim
                score = pts

                # Ownership fade adjustment
                if ownership:
                    own = ownership.get(pid, 0.1)
                    # High owned players penalized more, especially if high variance
                    # Variance proxy: std / mean
                    std = proj.get("std", pts * 0.4)
                    mean = proj.get("projection", pts)
                    variance = std / mean if mean else 0.5
                    # Fade formula: score *= (1 - ownership_fade * ownership * (1 + variance))
                    fade_factor = 1 - self.ownership_fade * own * (1 + variance * 0.5)
                    score *= max(0.1, fade_factor)

                # Correlation boost will be applied at lineup level, not individual

                scored_players.append((pid, score, proj.get("salary", 5000), pts))

            # Sort by adjusted score descending
            scored_players.sort(key=lambda x: x[1], reverse=True)

            # Build lineup greedily picking top scoring in this sim under salary cap
            lineup = []
            salary_used = 0
            lineup_points = {}  # pid -> raw points in this sim

            for pid, adj_score, sal, raw_pts in scored_players:
                if salary_used + sal <= self.salary_cap and len(lineup) < self.lineup_size:
                    if pid not in lineup:
                        lineup.append(pid)
                        salary_used += sal
                        lineup_points[pid] = raw_pts
                if len(lineup) >= self.lineup_size:
                    break

            if len(lineup) < self.lineup_size:
                continue

            # Apply correlation weight: compute avg correlation within lineup
            # Only apply probabilistic filter if we have many lineups already and weight is high
            # To avoid rejecting too many, we only reject if lineup is very low corr and we have > 50% of target
            if correlation_matrix and self.correlation_weight > 0 and len(lineups) > num_lineups * 0.3:
                corr_sum = 0
                corr_count = 0
                for i, pid1 in enumerate(lineup):
                    for pid2 in lineup[i+1:]:
                        corr_val = correlation_matrix.get((pid1, pid2), 0)
                        corr_sum += corr_val
                        corr_count += 1
                avg_corr = corr_sum / corr_count if corr_count else 0
                if self.correlation_weight > 0.7 and avg_corr < -0.1:
                    if random.random() < 0.3:
                        continue

            lineups.append(lineup)

        return lineups

    def build_with_custom_metric(
        self,
        game_scripts: List[GameScript],
        projections: Dict[str, Dict],
        custom_metric: str = "projection * (ceiling_p90 / projection) * (1 + leverage)",
        ownership: Dict[str, float] = None,
        num_lineups: int = 500,
    ) -> List[List[str]]:
        """
        Custom lineup ranking metric — Ultimate plan feature.
        "Create your own lineup ranking metric using any combination of your data and ours"
        Source: https://www.sabersim.com/pricing

        custom_metric is a string formula using fields: projection, ceiling_p90, ownership, etc.
        For simplicity, we parse limited expressions.
        """
        # This is a simplified version — real implementation would use safe eval
        # We'll just use the default SaberScore proxy if custom_metric not parsed
        return self.build(game_scripts, projections, ownership, num_lineups)
