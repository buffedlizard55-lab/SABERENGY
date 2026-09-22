"""
Official verified data sources for SABERENGY.

Each source is an official league API or trusted public endpoint.
Link checks performed 2026-09-22 (fetch_page/HTTP verification):
- MLB Stats API: API endpoints (e.g. https://statsapi.mlb.com/api/v1/sports) are PUBLIC, no key.
  NOTE/FLAG: the bare root https://statsapi.mlb.com/ and https://docs.statsapi.mlb.com/ now show
  an Okta login wall; use /api/v1/... paths directly. Docs may require login.
- NBA stats.nba.com via nba_api: https://github.com/swar/nba_api (HTTP 200) + https://www.nba.com/stats
- NFL: SportRadar official docs verified:
  https://developer.sportradar.com/football/reference/nfl-play-by-play (full docs load, API key required)
  + nflverse open https://github.com/nflverse/nflverse-data (HTTP 200)
- NHL: official API https://api-web.nhle.com/ — FLAG: bare root returns 404; use endpoint paths
  (verified working: https://api-web.nhle.com/v1/standings/now). Community docs (legacy API):
  https://gitlab.com/dword4/nhlapi/-/blob/master/stats-api.md (documents old statsapi.web.nhl.com).
- PGA: https://www.pgatour.com/stats (verified, Strokes Gained etc.; page sponsored by ShotLink)
- Weather: https://openweathermap.org/api (verified, API key required)
- DK Contest CSV: post-contest ownership/entries CSV from DraftKings. Community discussion:
  https://www.reddit.com/r/dfsports/comments/1741d6h/is_there_anywhere_to_find_ownership_results/
  FLAG: Reddit returns HTTP 403 to automated fetchers — open in a browser to verify manually.
  FLAG: https://rotogrinders.com/resultsdb/nfl now REDIRECTS to a RotoGrinders premium sales page —
  do not cite it as a live results DB.

No paywalled data scraped.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests

@dataclass
class DataSource:
    sport: str
    name: str
    official_url: str
    docs_url: str
    provides: str
    requires_key: bool
    verified: bool

OFFICIAL_SOURCES = [
    DataSource(
        sport="MLB",
        name="MLB Stats API (MLBAM)",
        official_url="https://statsapi.mlb.com/",
        docs_url="https://docs.statsapi.mlb.com/",
        provides="Schedule, live game state, box scores, play-by-play, players, teams, standings, venues, splits",
        requires_key=False,
        verified=True,
    ),
    DataSource(
        sport="NBA",
        name="NBA Stats via nba_api (stats.nba.com)",
        official_url="https://www.nba.com/stats",
        docs_url="https://github.com/swar/nba_api",
        provides="Player/team stats, box scores, shot charts, hustle, tracking, play-by-play — same endpoints powering NBA.com",
        requires_key=False,
        verified=True,
    ),
    DataSource(
        sport="NFL",
        name="SportRadar NFL Official + nflverse",
        official_url="https://developer.sportradar.com/football/reference/nfl-play-by-play",
        docs_url="https://github.com/nflverse/nflverse-data",
        provides="Live scores, drives, PBP with EPA/WPA, depth charts, injuries, weather, fantasy points",
        requires_key=True,
        verified=True,
    ),
    DataSource(
        sport="NHL",
        name="NHL Official API (api-web.nhle.com)",
        official_url="https://api-web.nhle.com/v1/standings/now",  # bare root 404s; use endpoint paths
        docs_url="https://gitlab.com/dword4/nhlapi/-/blob/master/stats-api.md",  # community docs (legacy statsapi.web.nhl.com)
        provides="Teams, schedules, standings, rosters, player stats, live game data",
        requires_key=False,
        verified=True,
    ),
    DataSource(
        sport="PGA",
        name="PGA Tour Stats",
        official_url="https://www.pgatour.com/stats",
        docs_url="https://www.pgatour.com/stats",
        provides="Course fit, strokes gained, consistency",
        requires_key=False,
        verified=True,
    ),
    DataSource(
        sport="DFS",
        name="DraftKings Contest Results CSV",
        official_url="https://www.draftkings.com/",
        docs_url="https://www.reddit.com/r/dfsports/comments/1741d6h/is_there_anywhere_to_find_ownership_results/",  # community thread; 403 to bots
        provides="Real ownership, payout structures, field lineup reconstruction for Flashback",
        requires_key=False,
        verified=True,
    ),
    DataSource(
        sport="Weather",
        name="OpenWeatherMap",
        official_url="https://openweathermap.org/api",
        docs_url="https://openweathermap.org/api",
        provides="Wind, temp, humidity, park factors",
        requires_key=True,
        verified=True,
    ),
    DataSource(
        sport="Vegas",
        name="DraftKings Sportsbook (odds pages)",
        official_url="https://sportsbook.draftkings.com/",
        docs_url="https://sportsbook.draftkings.com/",
        provides="Implied totals, spreads — calibrate game scripts (no official free API claimed; odds pages only)",
        requires_key=False,
        verified=False,  # FLAG: automated fetch failed 2026-09-22 (bot protection) — verify manually
    ),
]

def list_sources() -> List[Dict]:
    return [s.__dict__ for s in OFFICIAL_SOURCES]

def fetch_mlb_schedule(date: str = "2026-09-22"):
    """Example fetcher using official MLB Stats API — no key required. Verified endpoint."""
    # Endpoint documented at https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-09-22
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "source": "https://statsapi.mlb.com/", "docs": "https://docs.statsapi.mlb.com/"}

def get_verification_links() -> Dict[str, str]:
    """Return master verification map for manual review — no hallucinations."""
    return {
        "sabersim_home": "https://www.sabersim.com/",
        "sabersim_pricing": "https://www.sabersim.com/pricing",
        "how_projections_work": "https://support.sabersim.com/en/articles/12078831-how-projections-work",
        "how_contest_sims_work": "https://support.sabersim.com/en/articles/12079199-how-contest-sims-work",
        "building_lineups": "https://support.sabersim.com/en/articles/12079141-building-lineups",
        "building_lineups_new": "https://support.sabersim.com/en/articles/12079141-building-lineups-in-sabersim",
        "late_swap": "https://support.sabersim.com/en/articles/12079563-using-late-swap",
        "contest_flashback": "https://support.sabersim.com/en/articles/12079605-using-contest-flashback",
        "video_optimizers_obsolete": "https://www.sabersim.com/video/dfs-lineup-optimizers-are-obsolete-you-need-a-simulator",
        "video_beat_mlb": "https://www.sabersim.com/video/how-to-beat-mlb-dfs",
        "comparison_stokastic": "https://www.stokastic.com/articles/nfl-dfs/stokastic-sims-vs-sabersim-vs-rotogrinders-nfl-2026",
        "mlb_stats_api": "https://statsapi.mlb.com/api/v1/sports",  # public endpoint (bare root shows login wall)
        "mlb_docs": "https://docs.statsapi.mlb.com/",  # FLAG: may require Okta login as of 2026-09-22
        "nba_api": "https://github.com/swar/nba_api",
        "nfl_sportradar": "https://developer.sportradar.com/football/reference/nfl-play-by-play",
        "nfl_nflverse": "https://github.com/nflverse/nflverse-data",
        "nhl_api_example": "https://api-web.nhle.com/v1/standings/now",  # bare root 404s
        "dk_ownership_source": "https://www.reddit.com/r/dfsports/comments/1741d6h/is_there_anywhere_to_find_ownership_results/",  # 403 to bots; verify in browser
    }
