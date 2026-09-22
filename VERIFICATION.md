# VERIFICATION — No Hallucinations Guarantee

Master claim list for SABERENGY. Every row links its source for manual review.
All pages re-checked **2026-09-22** via direct page fetch (quote text confirmed present unless status says otherwise).

## Master Source List

| ID | Claim | Quote / Paraphrase from Source | Source URL | Status |
|----|-------|--------------------------------|------------|--------|
| V1 | Play-by-play simulator, thousands of times | "SaberSim uses a one-of-a-kind play-by-play simulator to build every game from scratch, one play at a time, thousands of times." | https://support.sabersim.com/en/articles/12078831-how-projections-work | ✓ Verified (page fetched) |
| V2 | Each sim includes strategy, play-calling, coaching decisions, game flow | "Each sim includes strategy, play-calling, coaching decisions, and game flow." | same | ✓ Verified |
| V3 | Point projection = average of sim outcomes | "When you see a player's point projection on your screen, you are looking at the average of their outcomes across all of those simulated trials." | same | ✓ Verified |
| V4 | Floor = 10th–25th, Median = 50th, Ceiling = 85th–95th percentile | "Floor Projections: ... 10th-25th percentile." / "The 50th percentile..." / "Ceiling ... 85th–95th percentile." | same | ✓ Verified |
| V5 | Ownership = contest-specific, field-based, dynamic | "Contes[t]-specific: A player might be 65% owned in a high-stakes single-entry but only 41% in a large-field MME." / "Field-based: Ownership is a descriptive statistic of our field lineups..." / "Dynamic: ... usually within minutes of breaking news." | same | ✓ Verified (note: docs say "**usually** within minutes") |
| V6 | Adjusted Ownership → OLD SaberScore as negative variable | "Adjusted Ownership feeds directly into OLD SaberScore as a negative variable, penalizing lineups overloaded with over-owned players..." | same | ✓ Verified |
| V7 | Contest Sims recreate contests top-to-bottom | "Every lineup is judged using: Real game outcomes ... Realistic opponent lineups ... Exact payout structures..." | https://support.sabersim.com/en/articles/12079199-how-contest-sims-work | ✓ Verified |
| V8 | 13 different contest types; industry-aggregated projections | "...ownership projections for 13 different contest types." / "...builds multiple sets of opponent lineups using industry-aggregated projections that reflect actual construction and ownership trends." | same | ✓ Verified |
| V9 | Stakes buckets | "Low Stakes: $4 and under ... Flagship: $4.01 to $30 ... Med Stakes: $30.01 to $99.99 ... High Stakes: $100 or more." | same | ✓ Verified |
| V10 | Contest sim metrics beyond pricing's four | "ROI, Median ROI, Max ROI, Min ROI, Win Rate, Cash Rate, ROI StDev, Dupes" (definitions in article) | same | ✓ Verified |
| V11 | Sim Mode builds from sims; stacks emerge organically | "Stacks emerge organically because the simulations reflect actual game outcomes: A QB + WR stack happens when they both excel in the same game script..." | https://support.sabersim.com/en/articles/12079141-building-lineups | ✓ Verified |
| V12 | Optimizer Mode = static projections only | "Optimizer Mode: Uses static projections only. You must create stacking rules and ownership fades manually. Useful for cash games or testing projections, but less effective for GPPs." (FAQ) | same | ✓ Verified |
| V13 | Correlation & Sim Diversity slider definitions | "Correlation Slider: Controls how strongly correlated plays are prioritized. Higher = more natural stacks and correlations..." / "Sim Diversity Slider: Controls how many different game simulations your lineups are drawn from. Higher = more variety across outcomes..." | same (alias slug `-in-sabersim` also resolves to same article) | ✓ Verified |
| V14 | Late Swap: Quick Swap, notifications, automatic resims | "Quick Swap: A red lightning bolt highlights ruled-out players..." / "Notifications: Browser and mobile alerts..." / "Automatic Resims: Every time projections or news update, SaberSim reruns its play-by-play sims..." | https://support.sabersim.com/en/articles/12079563-using-late-swap | ✓ Verified |
| V15 | Flashback: DK-only, collect lineups, 100k re-sim | "After a DraftKings contest completes, SaberSim takes all of the real lineups that were actually played in that contest." / "These real lineups are run through 100,000 slate simulations..." / "Currently available for DraftKings slates only" | https://support.sabersim.com/en/articles/12079605-using-contest-flashback | ✓ Verified |
| V16 | Sim ROI definition | "It shows the average return you'd expect if the contest were played out 100,000 times." | same | ✓ Verified |
| V17 | Pricing: $97 / $197 / $297, $7-for-7-days trial, 500 / 5,000 lineups | "$97 billed monthly" / "$197 billed monthly" / "$297 billed monthly" / "just $7 for 7 days" | https://www.sabersim.com/pricing | ✓ Verified |
| V18 | 100k-in-30s + ROI suite (pricing) | "Sim each lineup in your pool against a representative contest 100k times in 30 seconds or less." / "ROI, Cash Rate, Win Rate, and ROI Standard Deviation" | same | ✓ Verified |
| V19 | 13 contest types verbatim | "Flagship MME, Flagship 20-max, Flagship SE, High Stakes MME, High Stakes 20-Max, High Stakes SE, Low Stakes MME, Low Stakes 20-Max, Low Stakes SE, Medium Stakes MME, Medium Stakes 20-max, Medium Stakes SE, Winner-Take-All" | same | ✓ Verified (verbatim) |
| V20 | "18 sports. 4 sites. 1 platform." + exact list + 4 site logos | Section heading "18 sports. 4 sites. 1 platform." lists: NBA, NFL, MLB, NHL, MMA, PGA, SOCCER\*, TENNIS, NASCAR, LOL, CSGO, CFB, CBB\*, F1, UFL, COD\*, CFL\*, WNBA; note "*Optimizer only"; sites: DraftKings, FanDuel, OwnersBox, Yahoo! Sports | https://www.sabersim.com/ (final content section) | ✓ Verified (verbatim; 18 items) |
| V21 | Homepage sim tagline | "THEY PROJECT PLAYERS, WE SIMULATE GAMES — Our one-of-a-kind algorithm simulates every game thousands of times, play-by-play." | same | ✓ Verified |
| V22 | Third-party method summary (Stokastic, 2026-08-18) | "SaberSim's answer is play-by-play game simulation: ... thousands of simulated game scripts rather than one hand-set number, with correlations emerging naturally..." | https://www.stokastic.com/articles/nfl-dfs/stokastic-sims-vs-sabersim-vs-rotogrinders-nfl-2026 | ✓ Verified (THIRD-PARTY) |
| V23 | MLB Stats API public endpoints | `GET https://statsapi.mlb.com/api/v1/sports` returns JSON, no key (copyright "MLB Advanced Media"). ⚠ Bare root and docs root show Okta login as of 2026-09-22. | https://statsapi.mlb.com/api/v1/sports | ✓ Verified working endpoint; login-wall flagged |
| V24 | nba_api repo exists (HTTP 200) | Repository github.com/swar/nba_api — Python wrapper for stats.nba.com endpoints | https://github.com/swar/nba_api | ✓ Verified (HTTP 200) |
| V25 | SportRadar NFL Play-by-Play docs | Full API reference page loads (data points, TTL, update frequency); API key required | https://developer.sportradar.com/football/reference/nfl-play-by-play | ✓ Verified (page fetched) |
| V26 | nflverse-data repo exists (HTTP 200) | Open-source NFL data (pbp, rosters, etc.) | https://github.com/nflverse/nflverse-data | ✓ Verified (HTTP 200) |
| V27 | NHL official API works on endpoint paths | `GET https://api-web.nhle.com/v1/standings/now` returns JSON. ⚠ Bare root `https://api-web.nhle.com/` = HTTP 404. | https://api-web.nhle.com/v1/standings/now | ✓ Verified; root-404 flagged |
| V28 | NHL community docs (legacy API) | GitLab dword4/nhlapi stats-api.md exists; documents legacy `statsapi.web.nhl.com` | https://gitlab.com/dword4/nhlapi/-/blob/master/stats-api.md | ✓ Verified; LEGACY flagged |
| V29 | PGA Tour stats page | Loads with Strokes Gained, scoring, ShotLink sponsorship | https://www.pgatour.com/stats | ✓ Verified (page fetched) |
| V30 | OpenWeather API page | Weather API product page loads; API key required | https://openweathermap.org/api | ✓ Verified (page fetched) |
| V31 | SaberSim video pages exist | Titles: "DFS Lineup Optimizers Are Obsolete. You Need a Simulator." and "How to Beat MLB DFS" | https://www.sabersim.com/video/dfs-lineup-optimizers-are-obsolete-you-need-a-simulator · https://www.sabersim.com/video/how-to-beat-mlb-dfs | ⚠ Pages exist; VIDEO transcripts not in HTML — transcript quotes not machine-verifiable |
| V32 | Leverage = sim win rate − ownership (formula) | "Leverage score (sim win rate minus projected ownership)..." | https://onlydfs.com/blog/best-mlb-dfs-optimizer-tools-2026.html | ⚠ THIRD-PARTY affiliate blog (describes its own tool); page fetched OK. SaberSim's own leverage wording: "lineups that look different from the field" (Building Lineups) |
| V33 | DK ownership CSV community guidance | Reddit thread about downloading DK ownership CSVs | https://www.reddit.com/r/dfsports/comments/1741d6h/is_there_anywhere_to_find_ownership_results/ | ⚠ HTTP 403 to automated fetch — manual browser check required |

## How to Manually Verify

1. Open each URL in the table.
2. Use browser find (Ctrl+F) for the quoted text.
3. Confirm the quote exists verbatim (or the paraphrase is faithful).
4. For ⚠ rows: check the flag notes (login wall, 404, 403, video-only, third-party).

## Flags for Review (Honest Gaps — Not Hallucinations)

- **F0** DraftKings Sportsbook URL (used as a Vegas-odds example) failed automated fetch on 2026-09-22 (bot protection) — marked **unverified**, manual browser check required. No official free odds API is claimed.
- **F1** Proprietary coaching/strategy model approximated with open data — unquantified accuracy gap (early drafts cited "~5–10%"; that number was **unsourced** and has been removed).
- **F2** Industry-aggregated field projections — private to SaberSim; approximated with own sim projections.
- **F3** Live flagship ownership — requires partner/network data; post-contest DK CSV only.
- **F4** 13-contest behavioral heuristics — list verified, per-type weights proprietary/unverified.
- **F5** SaberScore / Adjusted-Ownership formulas — intent documented, exact math proprietary; proxies used.
- **F6** Ownership Fade slider behavior — video-sourced only (V31).
- **F7** Third-party leverage formula (V32) — affiliate source, not SaberSim-official.

## Irregularities Observed on SaberSim's Own Site (2026-09-22)

- Pricing page Pro/Ultimate tooltips contain **"Lorem ipsum dolor sit amet..."** placeholder copy.
- Pricing page optimizer sport list says **"USFL"** while homepage and projections list say **"UFL"**.

## No Hallucination Statement

As of 2026-09-22, every SaberSim feature description in this repo is: (a) directly quoted from a linked public page, (b) a faithful paraphrase of a linked page, (c) a third-party claim marked THIRD-PARTY, or (d) an approximation marked as a flag. No invented pricing, sports, or features. If you find any claim without a source, please open a GitHub issue with label `verification`.
