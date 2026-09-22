"""Load public NFL tables used by the projection model.

Primary schedule file (downloaded via the GitHub API, which this environment
can reach):
  https://github.com/nflverse/nfldata/blob/master/data/games.csv
  Repo: https://github.com/nflverse/nfldata
  GitHub API license field: null (no SPDX returned on 2026-09-22).
  File was updated the same day this loader was written. It is Lee Sharpe's
  public schedule table, not an official NFL feed.

Canonical weekly player stats (CC-BY-4.0):
  https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv
  License: https://github.com/nflverse/nflverse-data (CC-BY-4.0, confirmed via GitHub API 2026-09-22)
  The release tag `stats_player` lists stats_player_week_2026.csv.
  Direct download failed here: TLS to release-assets.githubusercontent.com
  closed the connection on 2026-09-22.

Fallback weekly file actually readable from this environment:
  https://github.com/cwalenciak/the-odds-line/tree/master/player_stats
  No SPDX license on that repository. Columns match a weekly counting-stat
  extract (GSIS ids, attempts, yards, TDs). It is used only when the
  canonical release asset cannot be downloaded, and it does not include 2026.
  Do not treat it as an official nflverse redistribution.
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

import pandas as pd

NFLDATA_GAMES_API = "https://api.github.com/repos/nflverse/nfldata/contents/data/games.csv"
NFLVERSE_WEEK_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_player/stats_player_week_{season}.csv"
)
MIRROR_API = (
    "https://api.github.com/repos/cwalenciak/the-odds-line/contents/"
    "player_stats/{season}_player_stats.csv"
)
CACHE = Path(__file__).resolve().parents[2] / "data" / "cache"


def _token() -> Optional[str]:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _get(url: str, timeout: int = 60) -> bytes:
    headers = {"User-Agent": "SABERENGY-public-data/1.1", "Accept": "application/vnd.github+json"}
    token = _token()
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _github_file(api_url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    meta = json.loads(_get(api_url).decode())
    blob_url = meta["url"] if "git/blobs" in meta.get("url", "") else (
        f"https://api.github.com/repos/{api_url.split('/repos/')[1].split('/contents/')[0]}/git/blobs/{meta['sha']}"
    )
    blob = json.loads(_get(blob_url).decode())
    if blob.get("encoding") != "base64":
        raise RuntimeError(f"unexpected blob encoding for {api_url}")
    dest.write_bytes(base64.b64decode(blob["content"]))
    return dest


def load_games(refresh: bool = False) -> pd.DataFrame:
    dest = CACHE / "nfldata_games.csv"
    if refresh and dest.exists():
        dest.unlink()
    path = _github_file(NFLDATA_GAMES_API, dest)
    frame = pd.read_csv(path)
    frame["season"] = frame["season"].astype(int)
    frame["week"] = frame["week"].astype(int)
    return frame


def load_player_weeks(seasons: tuple[int, ...] = (2023, 2024, 2025)) -> tuple[pd.DataFrame, dict]:
    """Load weekly player counting stats.

    Tries the canonical nflverse release first. On TLS/HTTP failure, uses the
    GitHub-contents mirror listed above and records that in `provenance`.
    """
    frames = []
    provenance = {"seasons": {}, "canonical_license": "CC-BY-4.0", "canonical_repo": "https://github.com/nflverse/nflverse-data"}
    for season in seasons:
        canonical = NFLVERSE_WEEK_URL.format(season=season)
        dest = CACHE / f"stats_player_week_{season}.csv"
        source = "nflverse-release"
        try:
            if not dest.exists() or dest.stat().st_size == 0:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(_get(canonical))
        except Exception as exc:
            source = "community-mirror"
            dest = CACHE / f"mirror_player_stats_{season}.csv"
            try:
                if not dest.exists() or dest.stat().st_size == 0:
                    _github_file(MIRROR_API.format(season=season), dest)
            except Exception as mirror_exc:
                provenance["seasons"][str(season)] = {
                    "status": "unavailable",
                    "canonical_url": canonical,
                    "canonical_error": f"{type(exc).__name__}: {exc}",
                    "mirror_error": f"{type(mirror_exc).__name__}: {mirror_exc}",
                }
                continue
            provenance["seasons"][str(season)] = {
                "status": "mirror",
                "canonical_url": canonical,
                "canonical_error": f"{type(exc).__name__}: {exc}",
                "mirror_url": f"https://github.com/cwalenciak/the-odds-line/blob/master/player_stats/{season}_player_stats.csv",
                "mirror_license": "none declared (GitHub API license field null on 2026-09-22)",
            }
        else:
                provenance["seasons"][str(season)] = {"status": "canonical", "url": canonical}
        frame = pd.read_csv(dest)
        frame["season"] = frame["season"].astype(int)
        frame["week"] = frame["week"].astype(int)
        frame["source_file"] = str(dest.name)
        frames.append(frame)
    if not frames:
        raise FileNotFoundError("no weekly player files could be loaded")
    out = pd.concat(frames, ignore_index=True)
    if "season_type" in out.columns:
        out = out[out["season_type"].fillna("REG") == "REG"].copy()
    statuses = {item.get("status") for item in provenance["seasons"].values()}
    if statuses == {"mirror"}:
        provenance["source_used"] = "community-mirror"
    elif statuses == {"canonical"}:
        provenance["source_used"] = "nflverse-release"
    elif not statuses:
        provenance["source_used"] = "none"
    else:
        provenance["source_used"] = "mixed:" + ",".join(sorted(str(item) for item in statuses))
    return out, provenance
