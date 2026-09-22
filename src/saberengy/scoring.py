"""DraftKings classic scoring used by SABERENGY.

Rules transcribed from the public DraftKings rules pages on 2026-09-22.
This is not a SaberSim formula. Counting stats we do not have (fumbles,
2-point conversions, return TDs, sacks, defensive turnovers) are omitted
and the omission is part of the function's documented scope.

NFL source: https://www.draftkings.com/help/rules/1/1
MLB source: https://www.draftkings.com/help/rules/2/2
"""

from __future__ import annotations

DK_NFL_RULES_URL = "https://www.draftkings.com/help/rules/1/1"
DK_MLB_RULES_URL = "https://www.draftkings.com/help/rules/2/2"
VERIFIED_ON = "2026-09-22"

# Stats this NFL scorer can apply. Anything else on the official table is
# listed in NFL_UNSCORED_EVENTS and must not be silently treated as zero
# without the caller saying so.
NFL_SCORED_EVENTS = (
    "passing_yards",
    "passing_tds",
    "passing_interceptions",
    "rushing_yards",
    "rushing_tds",
    "receptions",
    "receiving_yards",
    "receiving_tds",
    "points_allowed",
)
NFL_UNSCORED_EVENTS = (
    "fumble_lost",
    "two_point_conversion",
    "return_td",
    "offensive_fumble_recovery_td",
    "dst_sack",
    "dst_interception",
    "dst_fumble_recovery",
    "dst_safety",
    "dst_blocked_kick",
    "dst_return_td",
)


def dk_nfl_offense(
    *,
    passing_yards: float = 0.0,
    passing_tds: float = 0.0,
    passing_interceptions: float = 0.0,
    rushing_yards: float = 0.0,
    rushing_tds: float = 0.0,
    receptions: float = 0.0,
    receiving_yards: float = 0.0,
    receiving_tds: float = 0.0,
) -> float:
    """Partial DraftKings NFL offense score.

    Implements the yardage, touchdown, reception, interception, and
    100/300-yard bonus lines from the official NFL Classic table.
    Does not award fumble-lost, 2-point conversions, or return TDs.
    """
    points = 0.0
    points += 0.04 * passing_yards
    points += 4.0 * passing_tds
    points -= 1.0 * passing_interceptions
    if passing_yards >= 300:
        points += 3.0
    points += 0.1 * rushing_yards
    points += 6.0 * rushing_tds
    if rushing_yards >= 100:
        points += 3.0
    points += 1.0 * receptions
    points += 0.1 * receiving_yards
    points += 6.0 * receiving_tds
    if receiving_yards >= 100:
        points += 3.0
    return points


def dk_nfl_points_allowed(points_allowed: float) -> float:
    """DraftKings DST points-allowed tiers only.

    Official table (NFL Classic rules page):
    0 -> +10, 1-6 -> +7, 7-13 -> +4, 14-20 -> +1,
    21-27 -> 0, 28-34 -> -1, 35+ -> -4.
    Sacks, takeaways, and return scores are not included.
    """
    pa = points_allowed
    if pa <= 0:
        return 10.0
    if pa <= 6:
        return 7.0
    if pa <= 13:
        return 4.0
    if pa <= 20:
        return 1.0
    if pa <= 27:
        return 0.0
    if pa <= 34:
        return -1.0
    return -4.0


def dk_mlb_hitter(
    *,
    singles: float = 0.0,
    doubles: float = 0.0,
    triples: float = 0.0,
    home_runs: float = 0.0,
    rbi: float = 0.0,
    runs: float = 0.0,
    walks: float = 0.0,
    hit_by_pitch: float = 0.0,
    stolen_bases: float = 0.0,
) -> float:
    """DraftKings MLB Classic hitter score.

    Official table: 1B +3, 2B +5, 3B +8, HR +10, RBI +2, R +2,
    BB +2, HBP +2, SB +5. Caught stealing is not on the hitter table
    fetched 2026-09-22, so it is not scored.
    """
    return (
        3.0 * singles
        + 5.0 * doubles
        + 8.0 * triples
        + 10.0 * home_runs
        + 2.0 * rbi
        + 2.0 * runs
        + 2.0 * walks
        + 2.0 * hit_by_pitch
        + 5.0 * stolen_bases
    )


def dk_mlb_pitcher(
    *,
    outs: float = 0.0,
    strikeouts: float = 0.0,
    win: float = 0.0,
    earned_runs: float = 0.0,
    hits: float = 0.0,
    walks: float = 0.0,
    hit_batsmen: float = 0.0,
    complete_game: float = 0.0,
    complete_game_shutout: float = 0.0,
    no_hitter: float = 0.0,
) -> float:
    """DraftKings MLB Classic pitcher score.

    Official table: +2.25 per inning (+0.75 per out), K +2, W +4,
    ER -2, H -0.6, BB -0.6, HBP -0.6, CG +2.5, CGSO +2.5, NH +5.
    Hitter stats for pitchers are not counted, per the scoring notes.
    """
    return (
        0.75 * outs
        + 2.0 * strikeouts
        + 4.0 * win
        - 2.0 * earned_runs
        - 0.6 * hits
        - 0.6 * walks
        - 0.6 * hit_batsmen
        + 2.5 * complete_game
        + 2.5 * complete_game_shutout
        + 5.0 * no_hitter
    )


def singles_from_hits(*, hits: float, doubles: float, triples: float, home_runs: float) -> float:
    """1B = H - 2B - 3B - HR. Negative results are data errors, not scores."""
    value = hits - doubles - triples - home_runs
    if value < -1e-6:
        raise ValueError(
            f"hits ({hits}) < doubles+triples+home_runs ({doubles + triples + home_runs})"
        )
    return max(0.0, value)
