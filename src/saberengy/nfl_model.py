"""NFL game-script projection model.

This is an independent model. It is not SaberSim's play-by-play engine and
does not use SaberSim projections. It uses:

- schedule, scores, spread_line, total_line from nflverse/nfldata games.csv
- weekly counting stats from the loader in nfl_data.py
- DraftKings NFL Classic scoring in scoring.py (partial: no fumbles/2pt/DST
  sacks)

Spread convention was measured, not assumed. On 2018-2025 regular-season
rows in games.csv, corr(home_score - away_score, spread_line) is positive
(about 0.45). Example checked in the file: 2024 week 1 BAL @ KC,
spread_line +3.0, KC won 27-20. Positive spread_line is treated as the
expected home margin (home favored). If a future file flips the sign, the
pipeline refuses to run rather than silently inverting it.

Player projections for a test week use only rows with
(season, week) strictly before the test week. The player pool is people
who appeared in the prior `lookback_weeks` weeks, not people who happened
to record a stat in the test week.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .scoring import dk_nfl_offense, dk_nfl_points_allowed

OFFENSE_POSITIONS = ("QB", "RB", "WR", "TE")


@dataclass
class EnvironmentModel:
    spread_correlation: float
    spread_convention: str
    margin_residuals: np.ndarray
    total_residuals: np.ndarray
    pass_intercept: float
    pass_slope: float
    pass_std: float
    n_games: int
    example: dict


@dataclass
class PlayerRate:
    player_id: str
    player_name: str
    team: str
    position: str
    games: int
    mean_points: float
    attempt_share: float
    carry_share: float
    target_share: float
    yards_per_attempt: float
    yards_per_carry: float
    yards_per_target: float
    catch_rate: float
    pass_td_per_att: float
    int_per_att: float
    rush_td_per_carry: float
    rec_td_per_target: float


@dataclass
class SlateProjection:
    players: pd.DataFrame
    game_checks: dict
    environment: EnvironmentModel
    notes: List[str] = field(default_factory=list)


def _dk_row(row: pd.Series) -> float:
    return dk_nfl_offense(
        passing_yards=float(row.get("passing_yards") or 0),
        passing_tds=float(row.get("passing_tds") or 0),
        passing_interceptions=float(row.get("passing_interceptions") or 0),
        rushing_yards=float(row.get("rushing_yards") or 0),
        rushing_tds=float(row.get("rushing_tds") or 0),
        receptions=float(row.get("receptions") or 0),
        receiving_yards=float(row.get("receiving_yards") or 0),
        receiving_tds=float(row.get("receiving_tds") or 0),
    )


def fit_environment(games: pd.DataFrame, before: Tuple[int, int]) -> EnvironmentModel:
    """Fit on regular-season games strictly before (season, week)."""
    season, week = before
    frame = games[
        (games["game_type"] == "REG")
        & games["home_score"].notna()
        & games["spread_line"].notna()
        & games["total_line"].notna()
        & ((games["season"] < season) | ((games["season"] == season) & (games["week"] < week)))
    ].copy()
    if len(frame) < 100:
        raise ValueError(f"only {len(frame)} training games before {before}")
    margin = frame["home_score"] - frame["away_score"]
    corr = float(margin.corr(frame["spread_line"]))
    if corr <= 0:
        raise ValueError(
            "spread_line is not positively correlated with home margin "
            f"(corr={corr:.3f}). Refusing to guess the sign. "
            "Source file: nflverse/nfldata data/games.csv"
        )
    example_rows = frame[(frame["season"] == 2024) & (frame["week"] == 1) & (frame["home_team"] == "KC")]
    example = {}
    if len(example_rows):
        row = example_rows.iloc[0]
        example = {
            "game": f"{row.away_team} @ {row.home_team}",
            "season": int(row.season),
            "week": int(row.week),
            "spread_line": float(row.spread_line),
            "home_score": float(row.home_score),
            "away_score": float(row.away_score),
            "note": "positive spread_line treated as expected home margin",
        }
    residuals_m = (margin - frame["spread_line"]).to_numpy(dtype=float)
    residuals_t = ((frame["home_score"] + frame["away_score"]) - frame["total_line"]).to_numpy(dtype=float)
    return EnvironmentModel(
        spread_correlation=corr,
        spread_convention="positive spread_line = expected home margin (measured)",
        margin_residuals=residuals_m,
        total_residuals=residuals_t,
        pass_intercept=0.0,
        pass_slope=0.0,
        pass_std=8.0,
        n_games=int(len(frame)),
        example=example,
    )


def fit_pass_volume(players: pd.DataFrame, games: pd.DataFrame, before: Tuple[int, int]) -> Tuple[float, float, float, int]:
    """Team pass attempts ~ a + b * (team score - opponent score), training only."""
    season, week = before
    offense = players[
        (players["position"] == "QB")
        & ((players["season"] < season) | ((players["season"] == season) & (players["week"] < week)))
    ]
    team_week = (
        offense.groupby(["season", "week", "team"], as_index=False)["attempts"]
        .sum()
        .rename(columns={"attempts": "pass_attempts"})
    )
    home = games[["season", "week", "home_team", "away_team", "home_score", "away_score", "game_type"]].copy()
    home = home[home["game_type"] == "REG"]
    home["team"] = home["home_team"]
    home["point_diff"] = home["home_score"] - home["away_score"]
    away = games[["season", "week", "home_team", "away_team", "home_score", "away_score", "game_type"]].copy()
    away = away[away["game_type"] == "REG"]
    away["team"] = away["away_team"]
    away["point_diff"] = away["away_score"] - away["home_score"]
    long = pd.concat(
        [home[["season", "week", "team", "point_diff"]], away[["season", "week", "team", "point_diff"]]],
        ignore_index=True,
    )
    merged = team_week.merge(long, on=["season", "week", "team"], how="inner")
    merged = merged[merged["pass_attempts"] > 0]
    if len(merged) < 50:
        return 32.0, -0.15, 8.0, int(len(merged))
    x = merged["point_diff"].to_numpy(dtype=float)
    y = merged["pass_attempts"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (intercept + slope * x)
    return float(intercept), float(slope), float(np.std(resid)), int(len(merged))


def _rates_from_history(history: pd.DataFrame) -> Dict[str, PlayerRate]:
    rates: Dict[str, PlayerRate] = {}
    if history.empty:
        return rates
    history = history.copy()
    history["dk"] = history.apply(_dk_row, axis=1)
    for pid, group in history.groupby("player_id"):
        last = group.sort_values(["season", "week"]).iloc[-1]
        games = max(1, len(group))
        attempts = float(group["attempts"].sum())
        carries = float(group["carries"].sum())
        targets = float(group["targets"].sum())
        team_keys = group.groupby(["season", "week", "team"]).size().reset_index()
        # shares are computed later against teammates; store raw means here
        rates[str(pid)] = PlayerRate(
            player_id=str(pid),
            player_name=str(last["player_name"]),
            team=str(last["team"]),
            position=str(last["position"]),
            games=int(games),
            mean_points=float(group["dk"].mean()),
            attempt_share=attempts / games,
            carry_share=carries / games,
            target_share=targets / games,
            yards_per_attempt=float(group["passing_yards"].sum() / attempts) if attempts else 7.0,
            yards_per_carry=float(group["rushing_yards"].sum() / carries) if carries else 4.2,
            yards_per_target=float(group["receiving_yards"].sum() / targets) if targets else 8.0,
            catch_rate=float(group["receptions"].sum() / targets) if targets else 0.62,
            pass_td_per_att=float(group["passing_tds"].sum() / attempts) if attempts else 0.045,
            int_per_att=float(group["passing_interceptions"].sum() / attempts) if attempts else 0.025,
            rush_td_per_carry=float(group["rushing_tds"].sum() / carries) if carries else 0.03,
            rec_td_per_target=float(group["receiving_tds"].sum() / targets) if targets else 0.04,
        )
    return rates


def _normalize(values: np.ndarray) -> np.ndarray:
    total = float(values.sum())
    if total <= 0:
        return np.ones(len(values)) / max(1, len(values))
    return values / total


def _simulate_team(
    rng: np.random.Generator,
    roster: List[PlayerRate],
    point_diff: float,
    env: EnvironmentModel,
) -> Dict[str, dict]:
    if not roster:
        return {}
    exp_att = env.pass_intercept + env.pass_slope * point_diff
    attempts = int(max(8, round(rng.normal(exp_att, env.pass_std))))
    qbs = [p for p in roster if p.position == "QB" and p.attempt_share > 0]
    skill = [p for p in roster if p.position in {"WR", "TE", "RB"} and p.target_share > 0]
    rushers = [p for p in roster if p.position in {"RB", "QB", "WR", "TE"} and p.carry_share > 0]
    out: Dict[str, dict] = {p.player_id: _empty_stat(p) for p in roster}

    if qbs:
        shares = _normalize(np.array([p.attempt_share for p in qbs], dtype=float))
        qb_atts = rng.multinomial(attempts, shares)
        for player, att in zip(qbs, qb_atts):
            ypa = max(3.0, rng.normal(player.yards_per_attempt, 1.1))
            tds = int(rng.poisson(max(0.01, att * player.pass_td_per_att)))
            ints = int(rng.poisson(max(0.005, att * player.int_per_att)))
            out[player.player_id]["attempts"] = int(att)
            out[player.player_id]["passing_yards"] = float(att * ypa)
            out[player.player_id]["passing_tds"] = tds
            out[player.player_id]["passing_interceptions"] = ints

    if skill and attempts:
        shares = _normalize(np.array([p.target_share for p in skill], dtype=float))
        targets = rng.multinomial(attempts, shares)
        team_pass_yards = sum(v["passing_yards"] for v in out.values())
        ypt = np.array([max(1.0, p.yards_per_target) for p in skill])
        yard_weights = _normalize(targets * ypt)
        rec_yards = rng.multinomial(max(0, int(round(team_pass_yards))), yard_weights) if team_pass_yards else np.zeros(len(skill), dtype=int)
        team_pass_tds = sum(v["passing_tds"] for v in out.values())
        rec_tds = rng.multinomial(int(team_pass_tds), shares) if team_pass_tds else np.zeros(len(skill), dtype=int)
        for player, tgt, yards, tds in zip(skill, targets, rec_yards, rec_tds):
            catch = float(np.clip(rng.normal(player.catch_rate, 0.08), 0.35, 0.9))
            out[player.player_id]["targets"] = int(tgt)
            out[player.player_id]["receptions"] = int(rng.binomial(int(tgt), catch)) if tgt else 0
            out[player.player_id]["receiving_yards"] = float(yards)
            out[player.player_id]["receiving_tds"] = int(tds)

    # Rush volume rises when leading. Slope is estimated loosely from the
    # pass-volume fit: attempts not used on passes are not a full rush model.
    # Rush attempts are the player's own historical mean, scaled by game script.
    lead_boost = 1.0 + np.clip(point_diff, -21, 21) / 70.0
    if rushers:
        means = np.array([max(0.1, p.carry_share) for p in rushers])
        carries = rng.poisson(means * lead_boost)
        for player, carry in zip(rushers, carries):
            if carry <= 0:
                continue
            ypc = max(0.5, rng.normal(player.yards_per_carry, 1.0))
            tds = int(rng.poisson(max(0.001, carry * player.rush_td_per_carry)))
            out[player.player_id]["carries"] = int(carry)
            out[player.player_id]["rushing_yards"] = float(carry * ypc)
            out[player.player_id]["rushing_tds"] = tds
    return out


def _empty_stat(player: PlayerRate) -> dict:
    return {
        "player_id": player.player_id,
        "player_name": player.player_name,
        "team": player.team,
        "position": player.position,
        "attempts": 0,
        "passing_yards": 0.0,
        "passing_tds": 0,
        "passing_interceptions": 0,
        "carries": 0,
        "rushing_yards": 0.0,
        "rushing_tds": 0,
        "targets": 0,
        "receptions": 0,
        "receiving_yards": 0.0,
        "receiving_tds": 0,
    }


def _points_from_stat(stat: dict) -> float:
    return dk_nfl_offense(
        passing_yards=stat["passing_yards"],
        passing_tds=stat["passing_tds"],
        passing_interceptions=stat["passing_interceptions"],
        rushing_yards=stat["rushing_yards"],
        rushing_tds=stat["rushing_tds"],
        receptions=stat["receptions"],
        receiving_yards=stat["receiving_yards"],
        receiving_tds=stat["receiving_tds"],
    )


def project_week(
    games: pd.DataFrame,
    players: pd.DataFrame,
    season: int,
    week: int,
    n_sims: int = 400,
    seed: int = 7,
    lookback_weeks: int = 6,
) -> Tuple[pd.DataFrame, dict]:
    """Project one week. Training rows are strictly before that week."""
    rng = np.random.default_rng(seed)
    env = fit_environment(games, (season, week))
    intercept, slope, std, n_pass = fit_pass_volume(players, games, (season, week))
    env.pass_intercept = intercept
    env.pass_slope = slope
    env.pass_std = std

    history = players[
        (players["position"].isin(OFFENSE_POSITIONS))
        & ((players["season"] < season) | ((players["season"] == season) & (players["week"] < week)))
    ].copy()
    # pool: recent appearances only
    if season and week:
        recent = history[
            (history["season"] == season) & (history["week"] >= week - lookback_weeks)
        ]
        if recent.empty:
            # season boundary: use the end of the previous season present in history
            prev = history[history["season"] < season]
            if prev.empty:
                raise ValueError(f"no history before {season} week {week}")
            last_season = int(prev["season"].max())
            last_week = int(prev.loc[prev["season"] == last_season, "week"].max())
            recent = prev[(prev["season"] == last_season) & (prev["week"] >= last_week - lookback_weeks + 1)]
        history_for_rates = history
        pool = recent.sort_values(["season", "week"]).groupby("player_id", as_index=False).tail(1)
    else:
        pool = history.groupby("player_id", as_index=False).tail(1)
        history_for_rates = history

    rates = _rates_from_history(history_for_rates[history_for_rates["player_id"].isin(pool["player_id"])])
    slate = games[(games["season"] == season) & (games["week"] == week) & (games["game_type"] == "REG")].copy()
    if slate.empty:
        raise ValueError(f"no games for {season} week {week}")

    # map player to the team they most recently played for
    team_of = {pid: rates[pid].team for pid in rates}
    by_team: Dict[str, List[PlayerRate]] = {}
    for pid, rate in rates.items():
        by_team.setdefault(rate.team, []).append(rate)

    sim_points: Dict[str, List[float]] = {pid: [] for pid in rates}
    for _, game in slate.iterrows():
        if pd.isna(game["spread_line"]) or pd.isna(game["total_line"]):
            continue
        home = str(game["home_team"])
        away = str(game["away_team"])
        home_roster = by_team.get(home, [])
        away_roster = by_team.get(away, [])
        for _ in range(n_sims):
            margin = float(game["spread_line"]) + float(rng.choice(env.margin_residuals))
            total = max(6.0, float(game["total_line"]) + float(rng.choice(env.total_residuals)))
            home_score = max(0.0, (total + margin) / 2.0)
            away_score = max(0.0, (total - margin) / 2.0)
            home_stats = _simulate_team(rng, home_roster, home_score - away_score, env)
            away_stats = _simulate_team(rng, away_roster, away_score - home_score, env)
            for pid, stat in {**home_stats, **away_stats}.items():
                sim_points[pid].append(_points_from_stat(stat))
            # DST partial: points allowed = opponent score
            sim_points.setdefault(f"DST_{home}", []).append(dk_nfl_points_allowed(away_score))
            sim_points.setdefault(f"DST_{away}", []).append(dk_nfl_points_allowed(home_score))

    rows = []
    for pid, rate in rates.items():
        samples = sim_points.get(pid) or []
        if not samples:
            continue
        arr = np.array(samples, dtype=float)
        rows.append(
            {
                "player_id": pid,
                "player_name": rate.player_name,
                "team": rate.team,
                "position": rate.position,
                "game_id": _game_id_for_team(slate, rate.team),
                "projection": float(arr.mean()),
                "std": float(arr.std()),
                "floor_p10": float(np.percentile(arr, 10)),
                "p25": float(np.percentile(arr, 25)),
                "median_p50": float(np.percentile(arr, 50)),
                "ceiling_p85": float(np.percentile(arr, 85)),
                "ceiling_p90": float(np.percentile(arr, 90)),
                "p95": float(np.percentile(arr, 95)),
                "baseline_mean": rate.mean_points,
                "games_in_rate": rate.games,
                "scoring": "dk_nfl_offense_partial",
                "scoring_url": "https://www.draftkings.com/help/rules/1/1",
            }
        )
    for team in set(slate["home_team"]).union(set(slate["away_team"])):
        pid = f"DST_{team}"
        samples = sim_points.get(pid) or []
        if not samples:
            continue
        arr = np.array(samples, dtype=float)
        rows.append(
            {
                "player_id": pid,
                "player_name": f"{team} DST",
                "team": team,
                "position": "DST",
                "game_id": _game_id_for_team(slate, team),
                "projection": float(arr.mean()),
                "std": float(arr.std()),
                "floor_p10": float(np.percentile(arr, 10)),
                "p25": float(np.percentile(arr, 25)),
                "median_p50": float(np.percentile(arr, 50)),
                "ceiling_p85": float(np.percentile(arr, 85)),
                "ceiling_p90": float(np.percentile(arr, 90)),
                "p95": float(np.percentile(arr, 95)),
                "baseline_mean": float("nan"),
                "games_in_rate": 0,
                "scoring": "dk_nfl_dst_points_allowed_only",
                "scoring_url": "https://www.draftkings.com/help/rules/1/1",
            }
        )
    projected = pd.DataFrame(rows)
    actual = players[(players["season"] == season) & (players["week"] == week)].copy()
    if not actual.empty:
        actual["actual_dk"] = actual.apply(_dk_row, axis=1)
        actual = actual[["player_id", "actual_dk", "team", "position", "player_name"]]
        projected = projected.merge(actual, on="player_id", how="left", suffixes=("", "_actual"))
    else:
        projected["actual_dk"] = np.nan

    meta = {
        "season": season,
        "week": week,
        "n_sims": n_sims,
        "training_games": env.n_games,
        "spread_correlation": env.spread_correlation,
        "spread_convention": env.spread_convention,
        "spread_example": env.example,
        "pass_intercept": env.pass_intercept,
        "pass_slope": env.pass_slope,
        "pass_std": env.pass_std,
        "pass_fit_n": n_pass,
        "pool_size": int((projected["position"] != "DST").sum()) if not projected.empty else 0,
        "lookback_weeks": lookback_weeks,
        "team_of_note": len(team_of),
    }
    return projected, meta


def _game_id_for_team(slate: pd.DataFrame, team: str) -> str:
    hit = slate[(slate["home_team"] == team) | (slate["away_team"] == team)]
    if hit.empty:
        return ""
    row = hit.iloc[0]
    return f"{int(row.season)}_{int(row.week)}_{row.away_team}_{row.home_team}"


def actuals_for_week(players: pd.DataFrame, season: int, week: int) -> pd.DataFrame:
    frame = players[(players["season"] == season) & (players["week"] == week)].copy()
    if frame.empty:
        return frame
    frame["actual_dk"] = frame.apply(_dk_row, axis=1)
    return frame


def score_forecast(projected: pd.DataFrame) -> dict:
    """MAE of the sim mean vs the trailing-mean baseline, offense only."""
    frame = projected[projected["position"].isin(OFFENSE_POSITIONS)].copy()
    frame = frame[frame["actual_dk"].notna()]
    if frame.empty:
        return {"n": 0, "note": "no actuals joined; this week is not yet in the player file"}
    err_model = (frame["projection"] - frame["actual_dk"]).abs()
    err_base = (frame["baseline_mean"] - frame["actual_dk"]).abs()
    return {
        "n": int(len(frame)),
        "mae_model": float(err_model.mean()),
        "mae_trailing_mean": float(err_base.mean()),
        "model_beats_trailing_mean": bool(err_model.mean() < err_base.mean()),
        "correlation_model": float(frame["projection"].corr(frame["actual_dk"])),
        "correlation_trailing_mean": float(frame["baseline_mean"].corr(frame["actual_dk"])),
        "scoring": "partial DraftKings offense (no fumbles, 2-point conversions, or return TDs)",
        "scoring_url": "https://www.draftkings.com/help/rules/1/1",
    }


def game_forecast_check(games: pd.DataFrame, season: int, week: int, seed: int = 7, n_sims: int = 500) -> dict:
    """Forward-test the game environment on one week. No player file required."""
    rng = np.random.default_rng(seed)
    env = fit_environment(games, (season, week))
    slate = games[
        (games["season"] == season)
        & (games["week"] == week)
        & (games["game_type"] == "REG")
        & games["home_score"].notna()
        & games["spread_line"].notna()
        & games["total_line"].notna()
    ]
    if slate.empty:
        return {"n": 0, "note": "no completed games with a spread for this week"}
    abs_margin = []
    abs_total = []
    market_margin = []
    market_total = []
    for _, game in slate.iterrows():
        margins = float(game["spread_line"]) + rng.choice(env.margin_residuals, size=n_sims)
        totals = float(game["total_line"]) + rng.choice(env.total_residuals, size=n_sims)
        pred_margin = float(np.mean(margins))
        pred_total = float(np.mean(totals))
        actual_margin = float(game["home_score"] - game["away_score"])
        actual_total = float(game["home_score"] + game["away_score"])
        abs_margin.append(abs(pred_margin - actual_margin))
        abs_total.append(abs(pred_total - actual_total))
        market_margin.append(abs(float(game["spread_line"]) - actual_margin))
        market_total.append(abs(float(game["total_line"]) - actual_total))
    return {
        "n": int(len(slate)),
        "mae_margin_model": float(np.mean(abs_margin)),
        "mae_margin_market": float(np.mean(market_margin)),
        "mae_total_model": float(np.mean(abs_total)),
        "mae_total_market": float(np.mean(market_total)),
        "note": (
            "Model mean is the market line plus the training residual mean. "
            "It should be close to the market, not magically better. "
            "A large gap vs the market would mean the residual mean is biased."
        ),
        "training_games": env.n_games,
        "spread_correlation": env.spread_correlation,
        "spread_example": env.example,
    }
