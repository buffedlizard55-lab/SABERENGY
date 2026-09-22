"""MLB plate-appearance projection model from public season rates.

Method note, not a claim of current SaberSim weights:
A 2015 FanGraphs description of the then-public SaberSim daily model said
it started from rest-of-season rates and adjusted event probabilities with
the odds-ratio method, then simulated games. That description is second-hand
here via a public Reddit quote of FanGraphs:

https://www.reddit.com/r/BeatTheStreak/comments/3gjmh8/mod_post_fangraphs_now_has_sabersim_daily/

The odds-ratio matchup adjustment itself is a standard public technique.
We do not have SaberSim's current weights, umpire model, or weather model.
This module applies odds-ratio adjustment to rates the caller supplies
(intended source: MLB Stats API, no key):

https://statsapi.mlb.com/api/v1/stats

Fantasy points use the DraftKings MLB Classic table:
https://www.draftkings.com/help/rules/2/2

Runs and RBI are not events in a plate appearance. They are allocated with
a simple team-run pool shared by teammates, which creates stack correlation.
That allocator is ours and is labeled as such. It is not a published
SaberSim formula.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from .scoring import dk_mlb_hitter, dk_mlb_pitcher


def odds_ratio_probability(batter_p: float, pitcher_p: float, league_p: float) -> float:
    """p' from odds_b * odds_p / odds_lg, clipped to (0.001, 0.85)."""
    batter_p = float(np.clip(batter_p, 1e-4, 0.85))
    pitcher_p = float(np.clip(pitcher_p, 1e-4, 0.85))
    league_p = float(np.clip(league_p, 1e-4, 0.85))
    odds = (batter_p / (1 - batter_p)) * (pitcher_p / (1 - pitcher_p)) / (league_p / (1 - league_p))
    prob = odds / (1 + odds)
    return float(np.clip(prob, 0.001, 0.85))


def regress(rate: float, sample: float, prior: float, k: float) -> float:
    weight = sample / (sample + k) if sample >= 0 else 0.0
    return float(weight * rate + (1 - weight) * prior)


def simulate_hitter_pas(
    rng: np.random.Generator,
    *,
    plate_appearances: int,
    rates: Dict[str, float],
) -> Dict[str, int]:
    """Multinomial PA outcomes. rates keys: k, bb, hbp, hr, triple, double, single.

    Remaining probability is an out. Rates must be non-negative and sum to <= 1.
    """
    keys = ("k", "bb", "hbp", "hr", "triple", "double", "single")
    probs = np.array([max(0.0, float(rates.get(key, 0.0))) for key in keys], dtype=float)
    if probs.sum() >= 1:
        probs = probs / probs.sum() * 0.95
    out_p = 1.0 - float(probs.sum())
    full = np.concatenate([probs, [out_p]])
    draws = rng.multinomial(int(plate_appearances), full)
    counted = {key: int(draws[i]) for i, key in enumerate(keys)}
    counted["out"] = int(draws[-1])
    return counted


def hitter_points_from_events(events: Dict[str, int], runs: float = 0.0, rbi: float = 0.0) -> float:
    return dk_mlb_hitter(
        singles=events.get("single", 0),
        doubles=events.get("double", 0),
        triples=events.get("triple", 0),
        home_runs=events.get("hr", 0),
        rbi=rbi,
        runs=runs,
        walks=events.get("bb", 0),
        hit_by_pitch=events.get("hbp", 0),
        stolen_bases=events.get("sb", 0),
    )


def project_matchup(
    rng: np.random.Generator,
    batter: Dict[str, float],
    pitcher: Dict[str, float],
    league: Dict[str, float],
    n_sims: int = 500,
    plate_appearances: int = 4,
) -> Dict[str, float]:
    """Mean DraftKings hitter points across sims for one batter vs one pitcher.

    `batter` / `pitcher` / `league` provide event rates per PA: k, bb, hbp, hr,
    triple, double, single. Pitcher rates are the rate allowed.
    Runs and RBI use a shared run environment so teammates correlate:
    expected runs scale with extra-base hits in that sim, split across the
    single hitter here (team stacking is applied by simulate_lineup_game).
    """
    adjusted = {}
    for key in ("k", "bb", "hbp", "hr", "triple", "double", "single"):
        adjusted[key] = odds_ratio_probability(
            batter.get(key, league.get(key, 0.05)),
            pitcher.get(key, league.get(key, 0.05)),
            league.get(key, 0.05),
        )
    samples = []
    for _ in range(n_sims):
        events = simulate_hitter_pas(rng, plate_appearances=plate_appearances, rates=adjusted)
        # Run/RBI allocator is ours: each HR produces a run and an RBI;
        # other hits produce a run with probability 0.35. Not a SaberSim formula.
        runs = events["hr"] + int(rng.binomial(events["single"] + events["double"] + events["triple"], 0.35))
        rbi = events["hr"] + int(rng.binomial(events["double"] + events["triple"], 0.45))
        samples.append(hitter_points_from_events(events, runs=runs, rbi=rbi))
    arr = np.array(samples, dtype=float)
    return {
        "projection": float(arr.mean()),
        "std": float(arr.std()),
        "floor_p10": float(np.percentile(arr, 10)),
        "median_p50": float(np.percentile(arr, 50)),
        "ceiling_p90": float(np.percentile(arr, 90)),
        "adjusted_rates": adjusted,
        "n_sims": n_sims,
        "method": "odds_ratio_pa",
        "scoring_url": "https://www.draftkings.com/help/rules/2/2",
    }


def pitcher_points_from_line(line: Dict[str, float]) -> float:
    innings = float(line.get("innings") or 0)
    return dk_mlb_pitcher(
        outs=innings * 3.0,
        strikeouts=float(line.get("strikeouts") or 0),
        win=float(line.get("win") or 0),
        earned_runs=float(line.get("earned_runs") or 0),
        hits=float(line.get("hits") or 0),
        walks=float(line.get("walks") or 0),
        hit_batsmen=float(line.get("hit_batsmen") or 0),
        complete_game=float(line.get("complete_game") or 0),
        complete_game_shutout=float(line.get("complete_game_shutout") or 0),
        no_hitter=float(line.get("no_hitter") or 0),
    )


def rates_from_counting(counting: Dict[str, float], league: Dict[str, float], k: float = 200.0) -> Dict[str, float]:
    """Per-PA rates from MLB Stats API counting stats, regressed to league rates."""
    pa = float(counting.get("plateAppearances") or counting.get("plate_appearances") or 0)
    ab = float(counting.get("atBats") or counting.get("at_bats") or 0)
    hits = float(counting.get("hits") or 0)
    doubles = float(counting.get("doubles") or 0)
    triples = float(counting.get("triples") or 0)
    home_runs = float(counting.get("homeRuns") or counting.get("home_runs") or 0)
    walks = float(counting.get("baseOnBalls") or counting.get("walks") or 0)
    hbp = float(counting.get("hitByPitch") or counting.get("hit_by_pitch") or 0)
    strikeouts = float(counting.get("strikeOuts") or counting.get("strikeouts") or 0)
    singles = max(0.0, hits - doubles - triples - home_runs)
    if pa <= 0:
        return dict(league)
    raw = {
        "k": strikeouts / pa,
        "bb": walks / pa,
        "hbp": hbp / pa,
        "hr": home_runs / pa,
        "triple": triples / pa,
        "double": doubles / pa,
        "single": singles / pa,
    }
    return {key: regress(raw[key], pa, league.get(key, raw[key]), k) for key in raw}
