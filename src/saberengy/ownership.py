"""Ownership sketch from field lineups.

WARNING: FieldLineups.generate is not roster-legal. It samples player ids
by weight. It does not fill DraftKings slots, does not require players from
two games, and does not enforce the MLB hitter cap. Do not enter those
lineups. Position-legal research lineups come from optimizer.OptimizerMode
with roster.RosterRules, and only when a real salary file is present are
they salary-cap legal.

The 13 contest-type names are copied from the public pricing page. The
weights below are unvalidated guesses, not SaberSim's field model.

Ownership modeling — field lineups + contest-specific ownership.

Verified from:
- https://support.sabersim.com/en/articles/12078831-how-projections-work
  "Ownership Projections: Contest-specific, Field-based, Dynamic"
  "Ownership is a descriptive statistic of our field lineups, which are large sets of simulated lineups that represent how the field is expected to build for each contest type."
  "Dynamic: Ownership projections update automatically whenever simulations rerun, usually within minutes of breaking news"

- https://support.sabersim.com/en/articles/12079199-how-contest-sims-work
  "Opponents don’t play the same way in a low-stakes 150-max as in a high-stakes single-entry, so SaberSim doesn’t model them the same. Instead, it builds multiple sets of opponent lineups using industry-aggregated projections that reflect actual construction and ownership trends"
  "Field lineups are SaberSim’s projection of what your opponents are likely to play in a given contest."

- https://www.sabersim.com/pricing
  "Auto-updating ownership for 13 contests: Flagship MME, Flagship 20-max, Flagship SE, High Stakes MME, High Stakes 20-Max, High Stakes SE, Low Stakes MME, Low Stakes 20-Max, Low Stakes SE, Medium Stakes MME, Medium Stakes 20-max, Medium Stakes SE, Winner-Take-All"
  "Live-updating Flagship ownership"

The quotes above describe SaberSim. This module does not implement that product.
"""

from typing import Dict, List
import random
import warnings
import numpy as np
from collections import Counter

NOT_ROSTER_LEGAL = (
    "FieldLineups samples ids by weight. Those lineups are not DraftKings-legal: "
    "no slot fill, no two-game rule, no MLB hitter cap. Do not enter them."
)
_warned = False

# 13 contest types verbatim from pricing page — verified source: https://www.sabersim.com/pricing
CONTEST_TYPES_13 = [
    "Flagship MME",
    "Flagship 20-max",
    "Flagship SE",
    "High Stakes MME",
    "High Stakes 20-Max",
    "High Stakes SE",
    "Low Stakes MME",
    "Low Stakes 20-Max",
    "Low Stakes SE",
    "Medium Stakes MME",
    "Medium Stakes 20-max",
    "Medium Stakes SE",
    "Winner-Take-All",
]

class FieldLineups:
    """
    Generates field lineups — large sets of simulated opponent lineups that represent how field builds.

    Methodology (approximating SaberSim's industry-aggregated projections):
    - Field tends to play high projection + value players more often (chalk)
    - But also has some randomness — not all field lineups are optimal
    - Different contest types have different behaviors:
      * MME (150-max): more diversified, more low-owned punts, more stacks
      * SE (single entry): tighter, more chalk, more balanced
      * High Stakes: sharper, more optimal, less random
      * Low Stakes: more random, more favorite team bias
      * Winner-Take-All: more contrarian, higher variance

    These heuristics are flagged as approximation — exact SaberSim heuristics proprietary.
    """

    def __init__(self, contest_type: str = "Flagship MME", num_lineups: int = 10000, seed: int = 42):
        self.contest_type = contest_type
        self.num_lineups = num_lineups
        random.seed(seed)
        np.random.seed(seed)

    def _contest_heuristic(self) -> Dict[str, float]:
        """Return heuristics for contest type — flagged as approximation."""
        ct = self.contest_type
        # Defaults
        heuristics = {
            "chalk_bias": 0.7,  # how much field favors high projection
            "randomness": 0.3,  # how much randomness in selection
            "stack_rate": 0.6,  # % of lineups that stack
            "value_bias": 0.5,  # how much field chases value
        }
        if "MME" in ct:
            heuristics["randomness"] = 0.4
            heuristics["stack_rate"] = 0.75
            heuristics["chalk_bias"] = 0.6
        if "SE" in ct or "Single" in ct:
            heuristics["randomness"] = 0.2
            heuristics["chalk_bias"] = 0.8
            heuristics["stack_rate"] = 0.5
        if "High Stakes" in ct:
            heuristics["randomness"] = 0.15
            heuristics["chalk_bias"] = 0.85
            heuristics["value_bias"] = 0.7
        if "Low Stakes" in ct:
            heuristics["randomness"] = 0.5
            heuristics["chalk_bias"] = 0.5
        if "Winner-Take-All" in ct:
            heuristics["randomness"] = 0.45
            heuristics["chalk_bias"] = 0.4
            heuristics["stack_rate"] = 0.8
        return heuristics

    def generate(self, projections: Dict[str, Dict], salary_cap: int = 50000, lineup_size: int = 9) -> List[List[str]]:
        """
        projections: dict player_id -> {projection, salary, team, position, etc.}
        Returns: list of lineups, each lineup is list of player_ids
        """
        global _warned
        if not _warned:
            warnings.warn(NOT_ROSTER_LEGAL, UserWarning, stacklevel=2)
            _warned = True
        heuristic = self._contest_heuristic()
        player_ids = list(projections.keys())

        # Compute selection weights based on projection + value
        weights = []
        for pid in player_ids:
            proj = projections[pid]
            pts = proj.get("projection", 10)
            salary = proj.get("salary", 5000)
            value = pts / (salary / 1000) if salary else pts
            # Chalk bias: higher projection = higher weight
            w = (pts * heuristic["chalk_bias"] + value * heuristic["value_bias"] * 2)
            # Add randomness factor
            w = w * (1 + random.uniform(-heuristic["randomness"], heuristic["randomness"]))
            weights.append(max(0.01, w))

        # Normalize weights
        total = sum(weights)
        probs = [w / total for w in weights]

        # Edge case: lineup_size > population
        effective_lineup_size = min(lineup_size, len(player_ids))

        field_lineups = []
        for _ in range(self.num_lineups):
            # Sample lineup_size players without replacement using probs (approximate)
            # For simplicity, use numpy choice
            try:
                chosen = np.random.choice(player_ids, size=effective_lineup_size, replace=False, p=probs)
            except ValueError:
                # Fallback if probs don't sum to 1 due to float or size issues
                try:
                    chosen = random.sample(player_ids, effective_lineup_size)
                except ValueError:
                    chosen = player_ids  # fallback to all players if still fails
            field_lineups.append(list(chosen))

        return field_lineups


class OwnershipModel:
    """
    Ownership projections from field lineups.

    "Ownership is a descriptive statistic of our field lineups"
    Source: https://support.sabersim.com/en/articles/12078831-how-projections-work
    """

    def __init__(self, contest_type: str = "Flagship MME", num_field_lineups: int = 10000):
        self.contest_type = contest_type
        self.num_field_lineups = num_field_lineups
        self.field_generator = FieldLineups(contest_type, num_field_lineups)

    def project(self, projections: Dict[str, Dict]) -> Dict[str, float]:
        """
        Returns dict player_id -> ownership % (0-1)
        """
        field_lineups = self.field_generator.generate(projections)
        counter = Counter()
        for lineup in field_lineups:
            for pid in lineup:
                counter[pid] += 1

        ownership = {}
        for pid in projections.keys():
            ownership[pid] = counter.get(pid, 0) / self.num_field_lineups
        return ownership

    def project_all_contests(self, projections: Dict[str, Dict]) -> Dict[str, Dict[str, float]]:
        """
        Project ownership for all 13 contest types — matches SaberSim Ultimate feature.
        Source: https://www.sabersim.com/pricing — "Auto-updating ownership for 13 contests"
        Returns dict contest_type -> {player_id -> ownership}
        """
        all_own = {}
        for ct in CONTEST_TYPES_13:
            model = OwnershipModel(contest_type=ct, num_field_lineups=self.num_field_lineups)
            all_own[ct] = model.project(projections)
        return all_own

    def adjusted_ownership(self, projections: Dict[str, Dict], ownership: Dict[str, float]) -> Dict[str, float]:
        """
        Adjusted ownership identifies over- and under-owned players relative to ceiling.
        "Adjusted Ownership feeds directly into OLD SaberScore as a negative variable, penalizing lineups overloaded with over-owned players"
        Source: https://support.sabersim.com/en/articles/12078831-how-projections-work

        We implement as: adjusted = ownership - ceiling_probability
        If player is highly owned but low ceiling, adjusted positive (over-owned, bad)
        If low owned but high ceiling, adjusted negative (under-owned, good leverage)
        """
        adjusted = {}
        for pid, proj in projections.items():
            own = ownership.get(pid, 0)
            # Ceiling proxy: p90 / mean, higher ratio = more upside
            p90 = proj.get("ceiling_p90", proj.get("projection", 0) * 1.5)
            mean = proj.get("projection", 1)
            ceiling_ratio = p90 / mean if mean else 1
            # Ceiling probability proxy: chance to exceed 1.5x mean — approximated
            # For simplicity, ceiling_prob = normalized ceiling_ratio
            ceiling_prob = min(0.5, max(0.01, (ceiling_ratio - 1) * 0.3))
            # Adjusted: positive means over-owned
            adjusted[pid] = own - ceiling_prob
        return adjusted

    def leverage_score(self, projections: Dict[str, Dict], ownership: Dict[str, float], sim_win_rates: Dict[str, float] = None) -> Dict[str, float]:
        """
        Leverage proxy = Sim Win Rate - Projected Ownership.

        ATTRIBUTION (verified):
        - Third-party definition: "Leverage score (sim win rate minus projected ownership)"
          Source (THIRD-PARTY, affiliate blog — flagged): https://onlydfs.com/blog/best-mlb-dfs-optimizer-tools-2026.html
        - SaberSim's own official definition of leverage is qualitative:
          "Leverage: lineups that look different from the field."
          Source: https://support.sabersim.com/en/articles/12079141-building-lineups
        SaberSim does NOT publish an exact leverage formula — this is a proxy, flagged in LIMITATIONS.md.
        """
        leverage = {}
        for pid in projections.keys():
            own = ownership.get(pid, 0)
            win_rate = sim_win_rates.get(pid, 0) if sim_win_rates else projections[pid].get("projection", 0) / 100
            leverage[pid] = win_rate - own
        return leverage
