"""Unit tests for scoring, roster legality, and contest-sim metrics.

These do not need network access. The NFL walk-forward is covered by
`python -m saberengy.pipeline`, which writes docs/run_summary.json.
"""

from __future__ import annotations

import random
import sys
import unittest

import numpy as np

sys.path.insert(0, "src")

from saberengy.contest_sim import ContestSimulator
from saberengy.mlb_model import odds_ratio_probability, project_matchup, rates_from_counting
from saberengy.optimizer import OptimizerMode
from saberengy.roster import DK_MLB_CLASSIC, DK_NFL_CLASSIC, validate_lineup
from saberengy.scoring import (
    dk_mlb_hitter,
    dk_mlb_pitcher,
    dk_nfl_offense,
    dk_nfl_points_allowed,
    singles_from_hits,
)
from saberengy.simulation import GameScript, PlayerOutcome, Simulator


def _nfl_pool():
    players = {}
    games = [("G1", "A", "B"), ("G2", "C", "D")]
    template = [
        ("QB", "A", "G1", 22),
        ("RB", "A", "G1", 16),
        ("RB", "B", "G1", 14),
        ("WR", "A", "G1", 18),
        ("WR", "B", "G1", 15),
        ("WR", "C", "G2", 13),
        ("TE", "C", "G2", 11),
        ("RB", "D", "G2", 12),
        ("WR", "D", "G2", 10),
        ("DST", "A", "G1", 7),
        ("DST", "C", "G2", 6),
        ("QB", "C", "G2", 19),
        ("TE", "B", "G1", 9),
        ("WR", "A", "G1", 8),
    ]
    for i, (pos, team, game, proj) in enumerate(template):
        pid = f"P{i}"
        players[pid] = {
            "player_id": pid,
            "player_name": pid,
            "position": pos,
            "team": team,
            "game_id": game,
            "projection": proj,
            "std": 3,
            "salary": 4000 + i * 100,
        }
    return players


class ScoringTests(unittest.TestCase):
    def test_nfl_bonuses_match_rules_table(self):
        # 300 pass yards = 12, +3 bonus, 2 pass TD = 8, 1 INT = -1 -> 22
        self.assertAlmostEqual(
            dk_nfl_offense(passing_yards=300, passing_tds=2, passing_interceptions=1),
            22.0,
        )
        # 100 rush yards = 10 + 3 bonus + 6 TD = 19
        self.assertAlmostEqual(dk_nfl_offense(rushing_yards=100, rushing_tds=1), 19.0)
        # 5 receptions + 80 yards + 1 TD = 5 + 8 + 6 = 19
        self.assertAlmostEqual(
            dk_nfl_offense(receptions=5, receiving_yards=80, receiving_tds=1),
            19.0,
        )
        self.assertEqual(dk_nfl_points_allowed(0), 10)
        self.assertEqual(dk_nfl_points_allowed(6), 7)
        self.assertEqual(dk_nfl_points_allowed(13), 4)
        self.assertEqual(dk_nfl_points_allowed(20), 1)
        self.assertEqual(dk_nfl_points_allowed(27), 0)
        self.assertEqual(dk_nfl_points_allowed(34), -1)
        self.assertEqual(dk_nfl_points_allowed(35), -4)

    def test_mlb_table(self):
        self.assertAlmostEqual(dk_mlb_hitter(home_runs=1, rbi=1, runs=1), 14.0)
        self.assertAlmostEqual(singles_from_hits(hits=4, doubles=1, triples=1, home_runs=1), 1.0)
        # 6 outs = 2 IP = 4.5, 6 K = 12, win = 4, 1 ER = -2 -> 18.5
        self.assertAlmostEqual(dk_mlb_pitcher(outs=6, strikeouts=6, win=1, earned_runs=1), 18.5)

    def test_bad_hit_split_raises(self):
        with self.assertRaises(ValueError):
            singles_from_hits(hits=1, doubles=1, triples=1, home_runs=1)


class RosterTests(unittest.TestCase):
    def test_optimizer_respects_nfl_slots_and_two_games(self):
        pool = _nfl_pool()
        lineups = OptimizerMode(rules=DK_NFL_CLASSIC).build(pool, num_lineups=8, seed=2)
        self.assertGreater(len(lineups), 0)
        for lineup in lineups:
            ok, reason = validate_lineup(lineup, pool, DK_NFL_CLASSIC, enforce_salary=True)
            self.assertTrue(ok, reason)
            positions = [pool[pid]["position"] for pid in lineup]
            self.assertEqual(positions.count("QB"), 1)
            self.assertGreaterEqual(positions.count("RB"), 2)
            self.assertGreaterEqual(positions.count("WR"), 3)
            self.assertGreaterEqual(positions.count("TE"), 1)
            self.assertEqual(positions.count("DST"), 1)
            self.assertLessEqual(sum(pool[pid]["salary"] for pid in lineup), 50000)
            self.assertGreaterEqual(len({pool[pid]["game_id"] for pid in lineup}), 2)

    def test_two_qbs_rejected(self):
        players = {
            "q1": {"position": "QB", "team": "A", "game_id": "G1", "salary": 5000},
            "q2": {"position": "QB", "team": "C", "game_id": "G2", "salary": 5000},
        }
        ok, reason = validate_lineup(["q1", "q2"], players, DK_NFL_CLASSIC, enforce_salary=True)
        self.assertFalse(ok)
        self.assertIn("size", reason)

    def test_mlb_hitter_cap(self):
        ids = []
        players = {}
        slots = ["P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"]
        for i, pos in enumerate(slots):
            pid = f"m{i}"
            ids.append(pid)
            players[pid] = {
                "position": pos,
                "team": "NYY" if pos != "P" else ("NYY" if i == 0 else "BOS"),
                "game_id": "G1" if i < 8 else "G2",
                "salary": 4000,
            }
        ok, reason = validate_lineup(ids, players, DK_MLB_CLASSIC, enforce_salary=True)
        self.assertFalse(ok)
        self.assertIn("hitter", reason)


class ContestTests(unittest.TestCase):
    def test_metrics_and_rank_payout(self):
        scripts = []
        for sim in range(5):
            outcomes = [
                PlayerOutcome("A", "A", "T", "QB", 30, game_id="g", sim_index=sim),
                PlayerOutcome("B", "B", "T", "RB", 5, game_id="g", sim_index=sim),
                PlayerOutcome("C", "C", "U", "WR", 1, game_id="g", sim_index=sim),
            ]
            scripts.append(GameScript("g", sim, "H", "A", 0, 0, outcomes))
        sim = ContestSimulator([100, 0], num_sims=5, entry_fee=10, seed=1)
        result = sim.simulate([["A"], ["C"]], [["B"]], scripts)
        row = result["per_lineup"][0]
        self.assertGreater(row["roi"], result["per_lineup"][1]["roi"])
        self.assertLessEqual(row["min_roi"], row["median_roi"])
        self.assertLessEqual(row["median_roi"], row["max_roi"])
        self.assertIn("dupes", row)
        self.assertGreaterEqual(row["cash_rate"], row["win_rate"])


class ModelTests(unittest.TestCase):
    def test_odds_ratio_identity(self):
        # batter and pitcher at league rate -> unchanged
        self.assertAlmostEqual(odds_ratio_probability(0.2, 0.2, 0.2), 0.2, places=6)

    def test_matchup_is_finite(self):
        rng = np.random.default_rng(1)
        league = {"k": 0.22, "bb": 0.08, "hbp": 0.01, "hr": 0.03, "triple": 0.005, "double": 0.05, "single": 0.15}
        batter = rates_from_counting(
            {"plateAppearances": 400, "atBats": 350, "hits": 100, "doubles": 20, "triples": 2, "homeRuns": 15, "baseOnBalls": 40, "hitByPitch": 4, "strikeOuts": 80},
            league,
        )
        out = project_matchup(rng, batter, league, league, n_sims=40, plate_appearances=4)
        self.assertGreater(out["projection"], 0)
        self.assertLessEqual(out["floor_p10"], out["median_p50"])
        self.assertLessEqual(out["median_p50"], out["ceiling_p90"])

    def test_schematic_simulator_still_runs(self):
        sim = Simulator(sport="NFL", n_sims=5, seed=1)
        scripts = sim.run(
            [
                {
                    "game_id": "g",
                    "home_team": "H",
                    "away_team": "A",
                    "players": [{"id": "q", "name": "Q", "team": "H", "position": "QB", "projection": 18, "std": 4}],
                }
            ]
        )
        self.assertEqual(len(scripts), 5)


if __name__ == "__main__":
    unittest.main()
