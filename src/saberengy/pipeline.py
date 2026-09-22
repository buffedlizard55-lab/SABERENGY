"""Run the public-data projection and lineup pipeline.

No DraftKings salary file is fetched. Official salaries sit behind an
authenticated lobby. Lineups from this command are position-legal research
lineups, not contest entries, unless a salary column is present.

Usage (from the repo root):
  PYTHONPATH=src .venv/bin/python -m saberengy.pipeline
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .contest_sim import ContestSimulator
from .nfl_data import load_games, load_player_weeks
from .nfl_model import game_forecast_check, project_week, score_forecast
from .optimizer import OptimizerMode
from .roster import DK_NFL_CLASSIC, validate_lineup
from .simulation import GameScript, PlayerOutcome

ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = ROOT / "docs" / "run_summary.json"


def _projections_dict(frame: pd.DataFrame) -> dict:
    out = {}
    for row in frame.itertuples(index=False):
        out[row.player_id] = {
            "player_id": row.player_id,
            "player_name": row.player_name,
            "team": row.team,
            "position": row.position,
            "game_id": row.game_id,
            "projection": float(row.projection),
            "std": float(row.std) if pd.notna(row.std) else 0.0,
            "salary": None,
            "ceiling_p90": float(row.ceiling_p90),
        }
    return out


def _scripts_from_projection(frame: pd.DataFrame, n_sims: int, seed: int) -> list:
    """Build GameScript objects from each player's projected distribution.

    These are not play-by-play scripts. They are independent draws from the
    already-simulated projection distribution so the contest-sim and optimizer
    interfaces can be exercised. Correlation was already used inside
    nfl_model.project_week; these draws do not recreate that correlation.
    """
    rng = np.random.default_rng(seed)
    scripts = []
    rows = [row for row in frame.itertuples(index=False)]
    for sim_index in range(n_sims):
        outcomes = []
        for row in rows:
            std = float(row.std) if pd.notna(row.std) else 0.0
            points = max(0.0, float(rng.normal(row.projection, std)))
            outcomes.append(
                PlayerOutcome(
                    player_id=row.player_id,
                    player_name=row.player_name,
                    team=row.team,
                    position=row.position,
                    fantasy_points=points,
                    game_id=str(row.game_id),
                    sim_index=sim_index,
                )
            )
        scripts.append(
            GameScript(
                game_id="slate",
                sim_index=sim_index,
                home_team="",
                away_team="",
                home_score=0,
                away_score=0,
                player_outcomes=outcomes,
            )
        )
    return scripts


def _upcoming_week(games: pd.DataFrame) -> dict:
    frame = games[(games["season"] == 2026) & (games["game_type"] == "REG") & (games["week"] == 3)].copy()
    rows = []
    for row in frame.sort_values("gameday").itertuples(index=False):
        rows.append(
            {
                "gameday": str(row.gameday),
                "matchup": f"{row.away_team} @ {row.home_team}",
                "spread_line": None if pd.isna(row.spread_line) else float(row.spread_line),
                "total_line": None if pd.isna(row.total_line) else float(row.total_line),
                "away_qb": None if pd.isna(row.away_qb_name) else str(row.away_qb_name),
                "home_qb": None if pd.isna(row.home_qb_name) else str(row.home_qb_name),
                "played": bool(pd.notna(row.home_score)),
            }
        )
    return {
        "season": 2026,
        "week": 3,
        "source": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
        "spread_convention": "positive spread_line = expected home margin, measured on earlier seasons in the same file",
        "player_projections": "not produced — canonical 2026 weekly player file could not be downloaded",
        "games": rows,
    }


def _extreme_games(games: pd.DataFrame) -> list:
    frame = games[(games["season"] == 2026) & (games["game_type"] == "REG") & games["home_score"].notna()].copy()
    frame["total"] = frame["home_score"] + frame["away_score"]
    frame = frame.sort_values("total", ascending=False).head(3)
    rows = []
    for row in frame.itertuples(index=False):
        rows.append(
            {
                "week": int(row.week),
                "gameday": str(row.gameday),
                "matchup": f"{row.away_team} {row.away_score:.0f} @ {row.home_team} {row.home_score:.0f}",
                "spread_line": None if pd.isna(row.spread_line) else float(row.spread_line),
                "total_line": None if pd.isna(row.total_line) else float(row.total_line),
                "actual_total": float(row.total),
                "flag": "extreme total vs the posted total_line; review for data error before treating as a normal game",
            }
        )
    return rows


def run() -> dict:
    started = time.time()
    games = load_games()
    players, provenance = load_player_weeks((2023, 2024, 2025))
    game_checks = {
        "2026_week_1": game_forecast_check(games, 2026, 1, n_sims=300),
        "2026_week_2": game_forecast_check(games, 2026, 2, n_sims=300),
        "2026_week_3_not_played": game_forecast_check(games, 2026, 3, n_sims=50),
    }
    player_tests = {}
    lineup_report = {}
    for label, season, week, sims in (
        ("2024_week_17", 2024, 17, 80),
        ("2025_week_3", 2025, 3, 80),
    ):
        projected, meta = project_week(players=players, games=games, season=season, week=week, n_sims=sims, seed=11)
        metrics = score_forecast(projected)
        player_tests[label] = {"metrics": metrics, "model": meta}
        if label == "2025_week_3":
            usable = projected[projected["position"].isin(["QB", "RB", "WR", "TE", "DST"])].copy()
            # drop players with no game on the slate
            usable = usable[usable["game_id"].astype(str).str.len() > 0]
            proj = _projections_dict(usable)
            builder = OptimizerMode(rules=DK_NFL_CLASSIC)
            lineups = builder.build(proj, num_lineups=15, seed=3)
            legal = []
            for lineup in lineups:
                ok, reason = validate_lineup(lineup, proj, DK_NFL_CLASSIC, enforce_salary=False)
                legal.append({"ok": ok, "reason": reason, "players": lineup})
            scripts = _scripts_from_projection(usable, n_sims=40, seed=5)
            # Synthetic payout for the engine demo. Not an official contest.
            payout = [1000, 500, 300, 200, 150] + [100] * 10 + [20] * 20
            contest = ContestSimulator(payout, num_sims=40, entry_fee=10.0, seed=5)
            field = lineups[:10] if lineups else [["NONE"]]
            contest_result = contest.simulate(lineups[:5] or field, field, scripts) if lineups else {"summary": {}}
            lineup_report = {
                "slate": "2025 week 3 regular season, historical illustration only",
                "not_the_current_slate": True,
                "label": "research lineups, salary cap NOT applied",
                "reason": "DraftKings salaries were not available from a keyless public endpoint on 2026-09-22",
                "rules_url": DK_NFL_CLASSIC.source_url,
                "n_lineups": len(lineups),
                "all_position_legal": all(item["ok"] for item in legal) if legal else False,
                "salary_cap_applied": False,
                "name_note": "Names are copied from the weekly file. The community mirror abbreviates them (for example J.Goff). They are not a DraftKings player-pool export.",
                "sample": [
                    [proj[pid]["player_name"] + " " + proj[pid]["position"] for pid in lineup]
                    for lineup in lineups[:3]
                ],
                "contest_sim_note": "synthetic  payout table, not a real contest; independent redraws, correlation not re-applied",
                "contest_summary": {
                    **contest_result.get("summary", {}),
                    "interpretable": False,
                    "why_not_interpretable": "Field is the same 10 research lineups. ROI from that smoke test is not a contest result.",
                },
            }
            # fix the typo in note
            lineup_report["contest_sim_note"] = (
                "Synthetic payout table for the engine only. Not a real DraftKings contest. "
                "Redraws are independent; within-game correlation was used to build the projection, not this contest redraw."
            )

    summary = {
        "generated_on": "2026-09-22",
        "elapsed_seconds": round(time.time() - started, 2),
        "what_this_is": (
            "Independent DFS research pipeline. Not affiliated with SaberSim. "
            "No SaberSim paywall was accessed."
        ),
        "salary_status": {
            "official_salaries_used": False,
            "reason": "DraftKings player pools and salaries are published inside an authenticated lobby, not as a keyless public API we could fetch.",
            "rules_url": "https://www.draftkings.com/help/rules/1/1",
        },
        "data": {
            "games": {
                "url": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
                "rows": int(len(games)),
                "max_gameday": str(games["gameday"].max()),
                "license": "GitHub API returned null for nflverse/nfldata on 2026-09-22. Not marked CC-BY.",
            },
            "player_weeks": provenance,
        },
        "game_environment_forward_tests": game_checks,
        "player_forward_tests": player_tests,
        "lineups": lineup_report,
        "upcoming_nfl_week": _upcoming_week(games),
        "irregularities": _extreme_games(games),
        "blocked": [
            {
                "item": "nflverse stats_player_week_2026.csv",
                "url": "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv",
                "status": "asset is listed on the stats_player release; download failed TLS to release-assets.githubusercontent.com",
            },
            {
                "item": "MLB Stats API from this sandbox",
                "url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-09-22",
                "status": "TLS connection closed from the sandbox. The same URL returned JSON via an external fetch on 2026-09-22 (16 games). Live MLB slate was not scored inside the sandbox.",
            },
            {
                "item": "DraftKings salaries",
                "url": "https://www.draftkings.com/help/rules/1/1",
                "status": "rules page is public; salary file is not",
            },
        ],
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    return summary


def main() -> None:
    summary = run()
    print(json.dumps({k: summary[k] for k in ("elapsed_seconds", "player_forward_tests", "game_environment_forward_tests", "lineups")}, indent=2, default=str))


if __name__ == "__main__":
    main()
