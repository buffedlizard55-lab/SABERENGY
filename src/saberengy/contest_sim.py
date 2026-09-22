"""Contest simulation against a payout table.

Public description, not our formula claim:
https://support.sabersim.com/en/articles/12079199-how-contest-sims-work

Metrics implemented to match the names in that article:
ROI, Median ROI, Max ROI, Min ROI, Win Rate, Cash Rate, ROI StDev, Dupes.

Dupes here means the count of identical lineups in the supplied field.
SaberSim does not publish the duplication equation. This is a count, not
their number.

Payouts are assigned by rank against the supplied payout list. If the field
is larger than `max_field_per_sim`, a random subset is scored and the result
is marked approximate. That is a speed limit, not the "100k in 30 seconds"
claim on https://www.sabersim.com/pricing — we benchmark separately and do
not assert that claim.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, List, Sequence

import numpy as np

from .simulation import GameScript


class ContestSimulator:
    def __init__(
        self,
        payout_structure: List[float],
        num_sims: int = 1000,
        seed: int = 42,
        entry_fee: float = 10.0,
        max_field_per_sim: int = 1500,
    ):
        if entry_fee <= 0:
            raise ValueError("entry_fee must be positive")
        self.payout_structure = list(payout_structure)
        self.num_sims = int(num_sims)
        self.entry_fee = float(entry_fee)
        self.max_field_per_sim = int(max_field_per_sim)
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def simulate(
        self,
        my_lineups: List[List[str]],
        field_lineups: List[List[str]],
        game_scripts: List[GameScript],
        projections_lookup: Dict = None,
    ) -> Dict:
        by_sim = defaultdict(dict)
        for script in game_scripts:
            bucket = by_sim[script.sim_index]
            for outcome in script.player_outcomes:
                bucket[outcome.player_id] = bucket.get(outcome.player_id, 0.0) + outcome.fantasy_points
        sim_ids = list(by_sim)
        if not sim_ids:
            raise ValueError("No game scripts provided")
        if not my_lineups:
            raise ValueError("No lineups provided")

        rng = np.random.default_rng(self.seed)
        approximate_field = len(field_lineups) > self.max_field_per_sim
        roi_rows = np.zeros((len(my_lineups), self.num_sims), dtype=float)
        wins = np.zeros(len(my_lineups), dtype=int)
        cashes = np.zeros(len(my_lineups), dtype=int)
        dupes = [
            sum(1 for field in field_lineups if field == lineup)
            for lineup in my_lineups
        ]

        for sim_i in range(self.num_sims):
            points = by_sim[int(rng.choice(sim_ids))]
            my_scores = np.array([_score(lineup, points) for lineup in my_lineups], dtype=float)
            if approximate_field:
                idx = rng.choice(len(field_lineups), size=self.max_field_per_sim, replace=False)
                field = [field_lineups[i] for i in idx]
            else:
                field = field_lineups
            field_scores = np.array([_score(lineup, points) for lineup in field], dtype=float)
            all_scores = np.concatenate([my_scores, field_scores]) if len(field_scores) else my_scores
            order = np.argsort(-all_scores, kind="mergesort")
            ranks = np.empty(len(all_scores), dtype=int)
            ranks[order] = np.arange(1, len(all_scores) + 1)
            for i, score in enumerate(my_scores):
                rank = int(ranks[i])
                # ties: pay the best tied rank's prize once, do not invent a split formula
                tied = np.where(np.isclose(all_scores, score))[0]
                best_rank = int(ranks[tied].min()) if len(tied) else rank
                payout = _payout_for_rank(best_rank, self.payout_structure)
                roi_rows[i, sim_i] = (payout - self.entry_fee) / self.entry_fee
                if best_rank == 1:
                    wins[i] += 1
                if payout > 0:
                    cashes[i] += 1

        per_lineup = {}
        for i, lineup in enumerate(my_lineups):
            rois = roi_rows[i]
            per_lineup[i] = {
                "lineup_index": i,
                "lineup": lineup,
                "roi": float(np.mean(rois)),
                "median_roi": float(np.median(rois)),
                "max_roi": float(np.max(rois)),
                "min_roi": float(np.min(rois)),
                "roi_std": float(np.std(rois)),
                "win_rate": float(wins[i] / self.num_sims),
                "cash_rate": float(cashes[i] / self.num_sims),
                "dupes": int(dupes[i]),
            }
        return {
            "per_lineup": per_lineup,
            "summary": {
                "num_sims": self.num_sims,
                "num_my_lineups": len(my_lineups),
                "num_field_lineups": len(field_lineups),
                "field_subsampled": approximate_field,
                "max_field_per_sim": self.max_field_per_sim,
                "entry_fee": self.entry_fee,
                "payout_structure_head": self.payout_structure[:10],
                "metrics": [
                    "roi",
                    "median_roi",
                    "max_roi",
                    "min_roi",
                    "win_rate",
                    "cash_rate",
                    "roi_std",
                    "dupes",
                ],
                "source": "https://support.sabersim.com/en/articles/12079199-how-contest-sims-work",
            },
        }

    def flashback_sim(self, real_contest_lineups: List[List[str]], game_scripts: List[GameScript]) -> Dict:
        return self.simulate(real_contest_lineups, real_contest_lineups, game_scripts)


def _score(lineup: Sequence[str], points: Dict[str, float]) -> float:
    return float(sum(points.get(pid, 0.0) for pid in lineup))


def _payout_for_rank(rank: int, payouts: List[float]) -> float:
    if rank < 1:
        return 0.0
    if rank - 1 < len(payouts):
        return float(payouts[rank - 1])
    return 0.0
