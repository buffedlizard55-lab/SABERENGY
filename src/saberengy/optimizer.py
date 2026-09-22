"""Lineup builder with DraftKings roster constraints.

Sim mode samples a game script and builds the best legal lineup for that
script. That matches the public SaberSim description of building from
simulated scripts rather than a single average:

https://support.sabersim.com/en/articles/12079141-building-lineups

The slider formulas below are ours. SaberSim publishes the direction of
the Correlation and Sim Diversity sliders in that article. It does not
publish the equation. Ownership Fade is described on a video page whose
transcript is not in the HTML, so the fade formula is flagged as an
approximation.

Salary cap is enforced only when every candidate has a salary. Official
DraftKings salaries are not on a keyless public API we could fetch on
2026-09-22. Lineups built without salaries are labeled research lineups
and are not valid contest entries.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .roster import RosterRules, normalize_position, slot_order, validate_lineup
from .simulation import GameScript


class OptimizerMode:
    """Static-projection builder. SaberSim describes this as cash-oriented."""

    def __init__(self, salary_cap: int = 50000, lineup_size: int = 9, rules: Optional[RosterRules] = None):
        self.salary_cap = salary_cap
        self.lineup_size = lineup_size
        self.rules = rules

    def build(
        self,
        projections: Dict[str, Dict],
        num_lineups: int = 20,
        seed: int = 1,
    ) -> List[List[str]]:
        rng = random.Random(seed)
        if self.rules is None:
            return _legacy_greedy(projections, num_lineups, self.salary_cap, self.lineup_size, rng)
        return _build_many(
            projections,
            self.rules,
            num_lineups,
            rng,
            score_of=lambda pid, row: float(row.get("projection") or 0),
            enforce_salary=_salaries_present(projections),
        )


class SimOptimizer:
    def __init__(
        self,
        salary_cap: int = 50000,
        lineup_size: int = 9,
        correlation_weight: float = 0.5,
        sim_diversity: float = 0.5,
        ownership_fade: float = 0.3,
        seed: int = 42,
        rules: Optional[RosterRules] = None,
        max_exposure: float = 0.6,
    ):
        self.salary_cap = salary_cap
        self.lineup_size = lineup_size
        self.correlation_weight = correlation_weight
        self.sim_diversity = sim_diversity
        self.ownership_fade = ownership_fade
        self.seed = seed
        self.rules = rules
        self.max_exposure = max_exposure

    def build(
        self,
        game_scripts: List[GameScript],
        projections: Dict[str, Dict],
        ownership: Optional[Dict[str, float]] = None,
        num_lineups: int = 50,
        correlation_matrix: Optional[Dict[Tuple[str, str], float]] = None,
    ) -> List[List[str]]:
        rng = random.Random(self.seed)
        if not game_scripts:
            return OptimizerMode(self.salary_cap, self.lineup_size, self.rules).build(
                projections, num_lineups, seed=self.seed
            )
        if self.rules is None:
            return _legacy_from_scripts(
                game_scripts,
                projections,
                ownership or {},
                num_lineups,
                rng,
                self.salary_cap,
                self.lineup_size,
                self.sim_diversity,
                self.ownership_fade,
            )
        by_sim = defaultdict(dict)
        for script in game_scripts:
            for outcome in script.player_outcomes:
                by_sim[script.sim_index][outcome.player_id] = (
                    by_sim[script.sim_index].get(outcome.player_id, 0.0) + outcome.fantasy_points
                )
        sim_ids = list(by_sim)
        if not sim_ids:
            return []
        keep = max(1, int(len(sim_ids) * (0.15 + 0.85 * self.sim_diversity)))
        chosen_sims = sim_ids if keep >= len(sim_ids) else rng.sample(sim_ids, keep)
        enforce_salary = _salaries_present(projections)
        lineups: List[List[str]] = []
        exposure = defaultdict(int)
        attempts = 0
        while len(lineups) < num_lineups and attempts < num_lineups * 25:
            attempts += 1
            sim_idx = rng.choice(chosen_sims)
            points = by_sim[sim_idx]

            def score_of(pid: str, row: dict, points=points) -> float:
                base = float(points.get(pid, row.get("projection") or 0))
                own = (ownership or {}).get(pid, 0.0)
                std = float(row.get("std") or 0)
                mean = float(row.get("projection") or base or 1)
                variance = std / mean if mean else 0.4
                # Approximation of the video-described fade. Not an official equation.
                fade = 1.0 - self.ownership_fade * own * (1.0 + 0.5 * variance)
                return base * max(0.05, fade)

            lineup = _build_one(
                projections,
                self.rules,
                rng,
                score_of,
                enforce_salary=enforce_salary,
                correlation_weight=self.correlation_weight,
                correlation_matrix=correlation_matrix,
            )
            if lineup is None:
                continue
            if self.max_exposure < 1 and lineups:
                if any((exposure[pid] + 1) / num_lineups > self.max_exposure + 1e-9 for pid in lineup):
                    if rng.random() < 0.8:
                        continue
            ok, _reason = validate_lineup(lineup, projections, self.rules, enforce_salary=enforce_salary)
            if not ok:
                continue
            lineups.append(lineup)
            for pid in lineup:
                exposure[pid] += 1
        return lineups


def _legacy_from_scripts(
    game_scripts,
    projections,
    ownership,
    num_lineups,
    rng,
    salary_cap,
    lineup_size,
    sim_diversity,
    ownership_fade,
):
    """Position-unaware sampler kept for the synthetic demo only.

    These lineups are not DraftKings-legal. Pass RosterRules for legal builds.
    """
    by_sim = defaultdict(dict)
    for script in game_scripts:
        for outcome in script.player_outcomes:
            by_sim[script.sim_index][outcome.player_id] = (
                by_sim[script.sim_index].get(outcome.player_id, 0.0) + outcome.fantasy_points
            )
    sim_ids = list(by_sim)
    if not sim_ids:
        return []
    keep = max(1, int(len(sim_ids) * (0.15 + 0.85 * sim_diversity)))
    chosen = sim_ids if keep >= len(sim_ids) else rng.sample(sim_ids, keep)
    lineups = []
    attempts = 0
    while len(lineups) < num_lineups and attempts < num_lineups * 20:
        attempts += 1
        points = by_sim[rng.choice(chosen)]
        ranked = sorted(points, key=lambda pid: points[pid], reverse=True)
        lineup = []
        spent = 0
        for pid in ranked:
            row = projections.get(pid, {})
            salary = int(row.get("salary") or 0)
            own = ownership.get(pid, 0.0)
            if ownership_fade and own > 0.45 and rng.random() < ownership_fade * 0.25:
                continue
            if spent + salary <= salary_cap and pid not in lineup:
                lineup.append(pid)
                spent += salary
            if len(lineup) >= lineup_size:
                break
        if len(lineup) == lineup_size:
            lineups.append(lineup)
    return lineups


def _salaries_present(projections: Dict[str, Dict]) -> bool:
    if not projections:
        return False
    return all(row.get("salary") is not None for row in projections.values())


def _legacy_greedy(projections, num_lineups, salary_cap, lineup_size, rng) -> List[List[str]]:
    """Kept so older callers without roster rules still return a sized lineup.

    These lineups are not DraftKings-legal. Callers that need legal lineups
    must pass RosterRules.
    """
    ranked = sorted(projections.items(), key=lambda item: item[1].get("projection", 0), reverse=True)
    size = min(lineup_size, len(ranked))
    lineups = []
    for _ in range(num_lineups):
        lineup = []
        spent = 0
        order = ranked[:]
        rng.shuffle(order)
        order.sort(key=lambda item: item[1].get("projection", 0), reverse=True)
        for pid, row in order:
            sal = int(row.get("salary") or 0)
            if pid in lineup:
                continue
            if spent + sal <= salary_cap and len(lineup) < size:
                lineup.append(pid)
                spent += sal
            if len(lineup) >= size:
                break
        if len(lineup) == size:
            lineups.append(lineup)
    return lineups


def _build_many(projections, rules, num_lineups, rng, score_of, enforce_salary) -> List[List[str]]:
    lineups = []
    attempts = 0
    while len(lineups) < num_lineups and attempts < num_lineups * 30:
        attempts += 1
        lineup = _build_one(projections, rules, rng, score_of, enforce_salary=enforce_salary)
        if lineup is None:
            continue
        ok, _ = validate_lineup(lineup, projections, rules, enforce_salary=enforce_salary)
        if ok:
            lineups.append(lineup)
    return lineups


def _build_one(
    projections: Dict[str, Dict],
    rules: RosterRules,
    rng: random.Random,
    score_of,
    enforce_salary: bool,
    correlation_weight: float = 0.0,
    correlation_matrix: Optional[Dict[Tuple[str, str], float]] = None,
) -> Optional[List[str]]:
    remaining = dict(projections)
    chosen: List[str] = []
    spent = 0
    for index in slot_order(rules):
        slot = rules.slots[index]
        slots_left = rules.lineup_size - len(chosen)
        candidates = []
        for pid, row in remaining.items():
            pos = normalize_position(rules.sport, row.get("position", ""))
            if pos not in slot.eligible:
                continue
            salary = int(row.get("salary") or 0)
            if enforce_salary and spent + salary > rules.salary_cap:
                continue
            score = score_of(pid, row)
            if correlation_weight and chosen and correlation_matrix:
                corr = np.mean([correlation_matrix.get((pid, other), 0.0) for other in chosen])
                score *= 1.0 + correlation_weight * float(corr)
            elif correlation_weight and chosen:
                same = sum(1 for other in chosen if projections[other].get("team") == row.get("team"))
                score *= 1.0 + correlation_weight * 0.15 * same
            candidates.append((pid, score, salary))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[1], reverse=True)
        pool = candidates[: max(4, len(candidates) // 4)]
        weights = [max(0.01, item[1]) for item in pool]
        pick = rng.choices(pool, weights=weights, k=1)[0]
        chosen.append(pick[0])
        spent += pick[2]
        del remaining[pick[0]]
        _ = slots_left
    games = {projections[pid].get("game_id") for pid in chosen}
    games.discard(None)
    games.discard("")
    if rules.min_games and len(games) < rules.min_games:
        return None
    return chosen
