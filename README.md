# SABERENGY — Open Source SaberSim Reverse Engineering

**Verified, No Hallucinations — All claims sourced from official pages (checked 2026-09-22)**

> Reverse engineering of [SaberSim.com](https://www.sabersim.com/) — a Monte Carlo DFS optimizer. This repo implements an open-source, clean-room Python reconstruction of the *methods documented in SaberSim's public support docs* (nothing paywalled or scraped).

GitHub Pages: https://buffedlizard55-lab.github.io/SABERENGY/ → `docs/index.html` (clean UI, all verified links)

## What is SaberSim? (Verified 2026-09-22)

SaberSim is a DFS optimizer that:

- **Core Method**: Play-by-play game simulation feeding the lineup builder — thousands of game scripts; correlations emerge naturally. Homepage tagline: *"THEY PROJECT PLAYERS, WE SIMULATE GAMES — Our one-of-a-kind algorithm simulates every game thousands of times, play-by-play."* Sources: [How Projections Work](https://support.sabersim.com/en/articles/12078831-how-projections-work) + [Homepage](https://www.sabersim.com/) + [Stokastic Comparison](https://www.stokastic.com/articles/nfl-dfs/stokastic-sims-vs-sabersim-vs-rotogrinders-nfl-2026)
- **Point Projections**: Come from thousands of play-by-play sims (not static averages); the projection you see is *"the average of their outcomes across all of those simulated trials."* Floor = 10th–25th percentile, Median = 50th, Ceiling = 85th–95th percentile. Source: [How Projections Work](https://support.sabersim.com/en/articles/12078831-how-projections-work)
- **Ownership**: Contest-specific (example: 65% in a high-stakes SE vs 41% in a large-field MME), field-based (descriptive statistic of field lineups), dynamic — updates *"usually within minutes of breaking news."* Source: same
- **Contest Sims**: Recreates contests using real game outcomes, realistic opponent lineups, exact payout structures. Pricing page: *"Sim each lineup in your pool against a representative contest 100k times in 30 seconds or less."* Metrics: ROI, Median ROI, Max ROI, Min ROI, Win Rate, Cash Rate, ROI StDev, Dupes. Sources: [How Contest Sims Work](https://support.sabersim.com/en/articles/12079199-how-contest-sims-work) + [Pricing](https://www.sabersim.com/pricing)
- **Stakes buckets** (verified): Low Stakes ≤ $4 · Flagship $4.01–$30 · Med Stakes $30.01–$99.99 · High Stakes ≥ $100. Source: [How Contest Sims Work](https://support.sabersim.com/en/articles/12079199-how-contest-sims-work)
- **Lineup Building**: Sim Mode builds from game scripts (stacks emerge organically); Optimizer Mode uses static projections only (*"You must create stacking rules and ownership fades manually"* — useful for cash, less effective for GPPs). Source: [Building Lineups](https://support.sabersim.com/en/articles/12079141-building-lineups) (alias slug: [building-lineups-in-sabersim](https://support.sabersim.com/en/articles/12079141-building-lineups-in-sabersim) — same article, both verified)
- **Sliders (official text)**: Correlation (*"Higher = more natural stacks and correlations"*) and Sim Diversity (*"Higher = more variety across outcomes"*). Source: [Building Lineups](https://support.sabersim.com/en/articles/12079141-building-lineups). **Ownership Fade** behavior (high-variance chalk faded more aggressively) is described in SaberSim's [video page](https://www.sabersim.com/video/dfs-lineup-optimizers-are-obsolete-you-need-a-simulator) — ⚠ video transcript is not machine-verifiable from page text; flagged.
- **Late Swap**: Quick Swap (red lightning bolt), full Late Swap Builds, notifications (browser/mobile), Games Panel, automatic re-sims, Delta Exposure. Source: [Using Late Swap](https://support.sabersim.com/en/articles/12079563-using-late-swap)
- **Contest Flashback**: DraftKings slates only; collects all real lineups, re-sims 100,000 times; metrics Sim ROI / Median Profit / 99th Profit / Average Dupes. Source: [Using Contest Flashback](https://support.sabersim.com/en/articles/12079605-using-contest-flashback)
- **Pricing**: Starter $97/mo (500 lineups), Pro $197/mo (5,000), Ultimate $297/mo (5,000 + contest sims + 13-contest ownership + ROI suite); trial $7 for 7 days. Source: [Pricing](https://www.sabersim.com/pricing)
- **13 Contest Types** (verbatim from pricing page): Flagship MME, Flagship 20-max, Flagship SE, High Stakes MME, High Stakes 20-Max, High Stakes SE, Low Stakes MME, Low Stakes 20-Max, Low Stakes SE, Medium Stakes MME, Medium Stakes 20-max, Medium Stakes SE, Winner-Take-All.
- **Sports/Sites**: Homepage section *"18 sports. 4 sites. 1 platform."* — NFL, NBA, MLB, NHL, MMA, PGA, SOCCER\*, TENNIS, NASCAR, LOL, CSGO, CFB, CBB\*, F1, UFL, COD\*, CFL\*, WNBA (\*optimizer only, per homepage note); sites: DraftKings, FanDuel, Yahoo! Sports, OwnersBox. Source: [Homepage](https://www.sabersim.com/)

## Data Quality — Official Sources Only

| Sport | Official Source | Verified Link (checked 2026-09-22) |
|-------|----------------|-----------------------------------|
| MLB | MLB Stats API (MLBAM) — public JSON endpoints, no key | https://statsapi.mlb.com/api/v1/sports (works) · ⚠ root https://statsapi.mlb.com/ and https://docs.statsapi.mlb.com/ show a login wall |
| NBA | stats.nba.com via nba_api (unofficial wrapper of official endpoints) | https://github.com/swar/nba_api (HTTP 200) · https://www.nba.com/stats |
| NFL | SportRadar official PBP (key required) + nflverse open historical | https://developer.sportradar.com/football/reference/nfl-play-by-play · https://github.com/nflverse/nflverse-data |
| NHL | NHL official API — ⚠ bare root 404s, use endpoint paths | https://api-web.nhle.com/v1/standings/now (works) · community/legacy docs: https://gitlab.com/dword4/nhlapi/-/blob/master/stats-api.md |
| PGA | PGA Tour official stats (ShotLink-powered) | https://www.pgatour.com/stats |
| DFS Contests | DraftKings post-contest CSV (manual download) | Community thread: https://www.reddit.com/r/dfsports/comments/1741d6h/is_there_anywhere_to_find_ownership_results/ (⚠ 403 to bots — open in browser) |
| Weather | OpenWeatherMap (key required) | https://openweathermap.org/api |
| Vegas odds | Sportsbook odds pages — ⚠ DK Sportsbook fetch blocked by bot protection (2026-09-22), verify manually; no official free API claimed | https://www.sportsbook.draftkings.com/ |

## Repo Structure

```
src/saberengy/
├── data_sources.py      # Official league APIs + verification links + link-check flags
├── simulation.py        # Play-by-play Monte Carlo engine (thousands of scripts)
├── projections.py       # Mean + percentiles (10/25/50/75/85/90/95) — floor/median/ceiling per docs
├── ownership.py         # Field lineups + 13 contest types + adjusted ownership + leverage proxy
├── contest_sim.py       # Contest Sims (100k default), ROI/Cash/Win/StdDev metrics
├── optimizer.py         # Sim Mode (sample from scripts) + Optimizer Mode (static)
├── late_swap.py         # Auto-resim loop + Quick Swap (drop-another-player logic)
├── flashback.py         # Contest Flashback analysis (Sim ROI vs actual)
└── demo.py              # End-to-end demo: slate -> sim -> projections -> ownership -> lineups -> contest sim

docs/index.html          # GitHub Pages site — clean UI, all verified sources
VERIFICATION.md          # Master claim-by-claim verification table
LIMITATIONS.md           # Honest gaps, flags, roadmap
```

## Quick Start

```bash
git clone https://github.com/buffedlizard55-lab/SABERENGY
cd SABERENGY
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m saberengy.demo --sport NFL --n-sims 1000 --n-lineups 100
# Outputs: output/projections.csv, output/ownership.csv, output/lineups.csv, output/contest_sim.json
PYTHONPATH=src python src/saberengy/tests/test_simulation.py   # test suite
```

## GitHub Pages

Clean, user-friendly site in `docs/index.html`:

- Verified feature matrix, line by line, with source links
- Sports & sites, pricing, projection-system deep dive
- Data-quality official sources with link-check status
- Limitations, irregularities, and roadmap

Enable Pages: Settings → Pages → Source: Deploy from branch → Branch: `main` → Folder: `/docs`
Live URL: https://buffedlizard55-lab.github.io/SABERENGY/

## Verification Checklist — No Hallucinations

Full table in `VERIFICATION.md` and `docs/index.html` Section 13. Highlights:

| # | Claim | Source |
|---|-------|--------|
| 1 | Play-by-play sim, thousands of times; projection = average of sim outcomes | https://support.sabersim.com/en/articles/12078831-how-projections-work |
| 2 | Floor 10–25th / Median 50th / Ceiling 85–95th percentiles | same |
| 3 | Ownership contest-specific (65%/41% example), field-based, dynamic ("usually within minutes") | same |
| 4 | Contest Sims: real outcomes + opponent lineups + exact payouts; 13 contest types | https://support.sabersim.com/en/articles/12079199-how-contest-sims-work |
| 5 | Stakes buckets: ≤$4 / $4.01–$30 / $30.01–$99.99 / ≥$100 | same |
| 6 | Sim Mode stacks emerge organically; Optimizer Mode static-projections FAQ | https://support.sabersim.com/en/articles/12079141-building-lineups |
| 7 | Correlation + Sim Diversity slider definitions | same |
| 8 | Late Swap: Quick Swap, notifications, automatic resims | https://support.sabersim.com/en/articles/12079563-using-late-swap |
| 9 | Flashback: DK-only, 100k re-sim, Sim ROI definition | https://support.sabersim.com/en/articles/12079605-using-contest-flashback |
| 10 | Pricing $97/$197/$297, $7 trial, 100k-in-30s, ROI suite, 13-contest list | https://www.sabersim.com/pricing |
| 11 | "18 sports. 4 sites. 1 platform." + exact 18-sport list | https://www.sabersim.com/ |
| 12 | Third-party method summary (Stokastic, Aug 18 2026) | https://www.stokastic.com/articles/nfl-dfs/stokastic-sims-vs-sabersim-vs-rotogrinders-nfl-2026 |

## Irregularities Flagged for Review

1. **SaberSim pricing page contains "Lorem ipsum" placeholder text** inside Pro/Ultimate feature blurbs (observed 2026-09-22) — likely a site bug on their side; quotes from those tooltips avoided.
2. **SaberSim's own pages disagree on UFL vs USFL**: homepage and projections list say "UFL"; pricing optimizer list says "USFL". Both transcribed as-is where quoted.
3. **Video-sourced claims** (Ownership Fade variance behavior) cannot be text-verified — page exists but transcripts are not in HTML.
4. **MLB docs login wall**: `statsapi.mlb.com` root and `docs.statsapi.mlb.com` now show Okta login; public API endpoints still work keyless.
5. **NHL API root 404**: must use `/v1/...` endpoint paths; community GitLab docs describe the legacy `statsapi.web.nhl.com` API.
6. **rotogrinders.com/resultsdb/nfl redirects to a sales page** — removed as a citation.
7. **Reddit thread returns 403 to automated fetchers** — kept as community source, verify manually in browser.
8. **Unsourced gap estimates** (e.g. "~5–10% accuracy gap") in earlier revisions were removed/relabeled as unsourced estimates.

## Limitations & Suggestions for Future Work

See `LIMITATIONS.md` for the full list. Headlines:

- **P0**: ML play-call tendencies on nflverse PBP; NBA minutes redistribution on injury; DK contest-CSV importer for Flashback; weather→park-factor integration; more unit tests (only 1 test today).
- **P1**: Validate 13-contest heuristics vs real contest CSVs; backtesting harness (Sim ROI vs realized ROI over 100 slates); real salary/position constraints per site; web UI.
- **Blocking full parity**: live flagship ownership (needs network effect/partner data), industry-aggregated field projections (private), calibrated proprietary weights (unknowable from public docs), cloud scale for 100k sims in 30s.

## License

MIT — Educational purposes only. Not affiliated with SaberSim.com. All trademarks belong to respective owners. Quotes are short excerpts from publicly accessible pages, provided solely for verification with attribution.

## Verification Methodology

Verification-first: every claim links a source for manual review. If you find any claim without a source, please open an issue labeled `verification`.
