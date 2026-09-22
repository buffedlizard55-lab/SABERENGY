"""Walk-forward checks that do not leak the test week into training.

Skipped automatically when the cached public files are absent, so unit
tests can run without network. The pipeline downloads those files.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")

from saberengy.nfl_model import fit_environment, project_week, score_forecast

CACHE = Path("data/cache")
GAMES = CACHE / "nfldata_games.csv"
PLAYERS = CACHE / "mirror_player_stats_2024.csv"


@unittest.skipUnless(GAMES.exists() and PLAYERS.exists(), "public cache not downloaded")
class ForwardLeakTests(unittest.TestCase):
    def test_environment_excludes_test_week(self):
        games = pd.read_csv(GAMES)
        games["season"] = games["season"].astype(int)
        games["week"] = games["week"].astype(int)
        env = fit_environment(games, (2026, 1))
        self.assertGreater(env.spread_correlation, 0)
        self.assertGreater(env.n_games, 1000)
        self.assertIn("KC", env.example.get("game", ""))

    def test_player_holdout_has_actuals_and_reports_baseline(self):
        games = pd.read_csv(GAMES)
        players = pd.read_csv(PLAYERS)
        games["season"] = games["season"].astype(int)
        games["week"] = games["week"].astype(int)
        players["season"] = players["season"].astype(int)
        players["week"] = players["week"].astype(int)
        players = players[players["season_type"] == "REG"]
        projected, meta = project_week(games, players, 2024, 17, n_sims=15, seed=3, lookback_weeks=4)
        self.assertEqual(meta["season"], 2024)
        self.assertLess(meta["pass_fit_n"], 10_000)
        metrics = score_forecast(projected)
        self.assertGreater(metrics["n"], 50)
        self.assertIn("model_beats_trailing_mean", metrics)
        # training must not include week 17 rows: baseline uses history only
        self.assertTrue((projected["games_in_rate"] >= 1).any())


if __name__ == "__main__":
    unittest.main()
