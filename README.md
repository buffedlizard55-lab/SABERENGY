# SABERENGY

Independent DFS research. Not affiliated with [SaberSim](https://www.sabersim.com/). No SaberSim account, trial, or paywall was used.

The public site is `docs/index.html`, served from GitHub Pages. It is generated from `docs/run_summary.json` so the numbers on the page are the numbers from the last pipeline run.

## What runs today

`python -m saberengy.pipeline` loads a public NFL schedule and weekly counting stats, projects two past weeks without using that week's stats, and writes the summary. It also builds position-legal research lineups for a past slate. Those lineups have no salaries. They are not contest entries.

The player model did not beat a trailing mean on 2024 week 17. A small MAE edge on 2025 week 3 is one week on a community mirror, not an established result. See the site for the figures.

## Data

| File | Link | What we use it for |
| --- | --- | --- |
| Schedule, spreads, totals | https://github.com/nflverse/nfldata/blob/master/data/games.csv | Game environment and the 2026 week 3 list. GitHub API license field was null on 2026-09-22. Not an official NFL feed. |
| Weekly player stats, preferred | https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv | CC-BY-4.0. Download failed here: TLS to the release CDN. |
| Weekly player stats, fallback | https://github.com/cwalenciak/the-odds-line/tree/master/player_stats | Used because the canonical file could not be downloaded. No SPDX license. Not an nflverse redistribution. |
| NFL scoring and roster | https://www.draftkings.com/help/rules/1/1 | Re-read 2026-09-22. Partial scorer: no fumbles, 2-point conversions, or return scores. |
| MLB scoring and roster | https://www.draftkings.com/help/rules/2/2 | Transcribed earlier. A re-fetch on this pass returned “Busy”, so it was not re-confirmed. |
| MLB rates, intended | https://statsapi.mlb.com/api/v1/stats | Keyless public API. This sandbox could not open TLS to it. No live MLB projection was produced. |

DraftKings salaries are inside an authenticated lobby. They were not fetched and not invented.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m unittest saberengy.tests.test_core saberengy.tests.test_nfl_forward
PYTHONPATH=src python -m saberengy.pipeline
PYTHONPATH=src python scripts/build_site.py
```

`python -m saberengy.demo` uses invented players and salaries so the old interfaces still run. It is not the forward test. Ownership lineups from that demo are not roster-legal.

## What is implemented

- Walk-forward NFL game environment and a player model that cannot see the test week.
- DraftKings NFL Classic slot rules, two-game minimum, and a salary cap when salaries exist.
- A contest simulator that ranks lineups against a caller-supplied payout list.
- An MLB odds-ratio plate-appearance function, tested on made-up rates only.

## What is not implemented

SaberSim's public pages describe play-by-play sims, contest-specific ownership, late swap, and flashback. Those pages are linked from the site and from `VERIFICATION.md`. This repo does not have their weights, their field, or their live ownership. The schematic simulator, the 13-type ownership guesses, late swap, and flashback are labeled as sketches. Late swap invents random news. Do not use it as an injury feed.

## Pages

GitHub Pages uses the repository root. `index.html` redirects to `docs/`. Live URL: https://buffedlizard55-lab.github.io/SABERENGY/

## License

MIT. Educational code. Trademarks belong to their owners. Short quotes in `VERIFICATION.md` are for checking the public pages, with links.
