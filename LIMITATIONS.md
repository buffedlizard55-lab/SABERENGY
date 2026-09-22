# Limitations

Checked 2026-09-22. This file is the gap list. It is not a claim that the gaps are small.

## Data we could not get

1. **Canonical 2026 weekly player file.** The release lists `stats_player_week_2026.csv`. Download to `release-assets.githubusercontent.com` failed TLS. No 2026 player projections were produced. Do not fill that file in by hand.
2. **MLB Stats API from this sandbox.** `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-09-22` closed the TLS connection here. An earlier external fetch saw games. This run did not score them.
3. **DraftKings salaries.** The rules page is public. The salary file is not a keyless endpoint we could fetch. Lineups without salaries are research lineups.
4. **Contest CSV ownership.** A community thread describes the DraftKings export. Automated fetch of that thread returned 403. No contest file was imported.

## Model limits

1. **The player model does not beat a trailing mean overall.** 2024 week 17 lost on MAE and correlation. 2025 week 3 had a small MAE edge and a tied correlation, on mirror data, with partial scoring and an early-season lookback. That is not a result to bet.
2. **The game check is the market plus a residual.** It is not a spread model with an edge.
3. **Scoring is partial.** NFL offense uses the yard, touchdown, reception, interception, and bonus lines from https://www.draftkings.com/help/rules/1/1. Fumbles, two-point conversions, and return scores are on that page and are not scored, because the weekly file does not have them. DST is points-allowed only.
4. **No NFL 8-player team cap.** The fetched rules page does not state one. A third-party guide does. It is not enforced.
5. **Names in the mirror are abbreviated.** Example shape: `J.Goff`. They are not a DraftKings export.
6. **MLB scoring was not re-read this pass.** The rules URL returned “Busy”. The table in `scoring.py` is an earlier transcription. Re-read it before using MLB points.
7. **Extreme 2026 totals stay in the file.** Week 1 CHI 59 at CAR 37 (total line 47.5) and two other high totals are flagged in the summary. They were not deleted.

## Code that is a sketch

1. **`simulation.py`** draws a total and a per-team factor. It does not simulate plays, and it does not load nflverse or a sportsbook.
2. **`ownership.py`** samples ids by weight. Those lineups are not roster-legal. The 13 contest names match the public pricing page. The weights are guesses.
3. **`late_swap.py`** invents a random OUT about 5% of the time. It does not poll an injury API.
4. **`flashback.py`** can rank lineups the caller already has. It does not download a contest.
5. **Slider formulas in `optimizer.py`** are ours. SaberSim publishes the direction of Correlation and Sim Diversity, not the equation.
6. **Contest-sim ROI in the pipeline is not interpretable.** The field is the same research lineups. The summary marks `interpretable: false`.

## Still open

- Repeat the player test on the canonical weekly file, including 2026 once that file downloads.
- Score a live MLB slate only after the Stats API is reachable and the rules page is re-read.
- Add salaries only from a file the operator can download without a paid trial.
- Validate ownership against a real contest export before trusting any ownership number.
- The 18-sport list on the SaberSim homepage is theirs. This repo has an NFL path and an unrun MLB rate function.
