# Limitations & Honest Gaps — Flags for Review

What we cannot fully replicate from public information, and what work remains.
These are honest gaps, not hallucinations — each has a source showing what *is* public and what is not.

## Proprietary Models We Approximate

### 1. Coaching / Strategy Tendency Model
- **Public claim**: "Each sim includes strategy, play-calling, coaching decisions, and game flow."
- **Source**: https://support.sabersim.com/en/articles/12078831-how-projections-work
- **What we have**: open historical PBP (nflverse), league APIs, Vegas totals as calibration anchors.
- **Gap**: exact weights/method are not public. **No numeric accuracy gap is claimed** (an earlier "~5–10%" figure was unsourced and has been removed).
- **Needed**: train models on years of PBP (play type, pace, usage); validate against held-out slates.
- **Flag**: APPROXIMATION — unquantified gap

### 2. Industry-Aggregated Projections for Field Lineups
- **Public claim**: "it builds multiple sets of opponent lineups using industry-aggregated projections that reflect actual construction and ownership trends"
- **Source**: https://support.sabersim.com/en/articles/12079199-how-contest-sims-work
- **What we have**: our own sim projections as a proxy input to field generation.
- **Gap**: SaberSim's aggregate inputs are private. Ownership error magnitude is **unmeasured** (earlier "2–5%" figure removed as unsourced).
- **Needed**: aggregate multiple free public projection sources; measure MAE vs post-contest DK CSV ownership.
- **Flag**: APPROXIMATION — needs calibration study

### 3. Live Flagship Ownership (real-time, pre-lock)
- **Public claim**: "See the actual ownership in the flagship contests in real time" / "Live-updating Flagship ownership"
- **Source**: https://www.sabersim.com/pricing
- **What we have**: simulated field lineups pre-lock; real ownership post-contest via DK CSV export.
- **Gap**: true live pre-lock flagship ownership needs partner data or a large opt-in user base.
- **Needed**: opt-in data sharing (e.g. browser extension) or DraftKings partnership.
- **Flag**: BLOCKED without network effect / partnership

### 4. 13 Contest-Type Heuristics
- **Public claim**: the 13-type list (verified verbatim on pricing page) + stake buckets (verified in Contest Sims article).
- **Sources**: https://www.sabersim.com/pricing · https://support.sabersim.com/en/articles/12079199-how-contest-sims-work
- **What we have**: hand-set heuristics per type (MME diversification, SE chalk, high-stakes sharpness, etc.).
- **Gap**: per-type behavioral parameters are proprietary; our heuristics are **unvalidated guesses**.
- **Needed**: collect 100+ real contests per type (DK CSVs), measure stack rates/ownership curves, fit parameters.
- **Flag**: APPROXIMATION — validation pending

### 5. SaberScore / Adjusted Ownership Math
- **Public claim**: "Adjusted Ownership feeds directly into OLD SaberScore as a negative variable..." + "Identifies over- and under-owned players relative to their ceiling outcomes."
- **Source**: https://support.sabersim.com/en/articles/12078831-how-projections-work
- **What we have**: proxy implementations (ceiling-probability proxy; leverage proxy = sim win rate − ownership from a **third-party** definition: https://onlydfs.com/blog/best-mlb-dfs-optimizer-tools-2026.html).
- **Gap**: exact formulas not published. SaberSim's own leverage wording is qualitative: "lineups that look different from the field" (Building Lineups article).
- **Flag**: PROXY — not exact

### 6. Sport Coverage
- **Public claim**: "18 sports. 4 sites. 1 platform." (homepage, exact list verified in VERIFICATION.md V20).
- **What we have**: NFL/NBA/MLB simulation paths implemented; others fall back to a generic simulator.
- **Gap**: PGA (course fit), MMA, NASCAR, esports etc. each need dedicated models + their official data feeds.
- **Flag**: PARTIAL — 3 sports with dedicated logic

### 7. Scale & Performance
- **Public claim**: "Sim each lineup ... 100k times in 30 seconds or less." (pricing page)
- **What we have**: vectorized-ish Python/numpy; demo runs 10k contest sims locally in seconds-to-minutes.
- **Gap**: no benchmark yet proving 100k ≤ 30s on typical hardware for large fields (field is subsampled to 1,000 lineups/sim — documented simplification in `contest_sim.py`).
- **Needed**: profiling, numpy vectorization of scoring, optional cloud batch.
- **Flag**: PERFORMANCE — claim not yet benchmarked locally

## Code-Level Limitations (honesty about our implementation)

1. **Synthetic demo slate**: `demo.py` uses generated players/salaries, not real DK salaries — real-slate ingestion from league APIs is scaffolded in `data_sources.py` but not wired end-to-end.
2. **Contest sim simplifications** (documented in code): cash line = 80th percentile of sampled scores rather than exact payout-table walk; field subsample ≤1,000 per sim; default $10 entry fee (now a constructor parameter).
3. **Position/salary rules**: optimizer enforces salary cap + lineup size but **not** positional slots (e.g. QB/RB/WR/TE/FLEX) — flagged as required for real DK/FD validity.
4. **Test coverage**: one end-to-end pipeline test exists (`tests/test_simulation.py`); no edge-case/fuzz/property tests yet.
5. **Late Swap news source**: `check_news()` simulates news (5% random OUT) — real injury feeds not wired (official endpoints listed in docstrings).
6. **Quick Swap**: re-implemented with drop-another-player fallback (bug fixed 2026-09-22); stack retention is a simple same-team preference, not full stack analysis.
7. **Reddit/robot restrictions**: DK CSV citation thread returns 403 to bots — manual browser verification required.

## What We CAN Replicate (Verified — See VERIFICATION.md)

- Play-by-play simulation concept → `simulation.py`
- Mean + percentile projections (floor/median/ceiling bands per docs) → `projections.py`
- Field lineups + contest-specific ownership + 13-type sweep → `ownership.py`
- Contest Sims concept (scripts + field + payout table → ROI/Win/Cash/StdDev) → `contest_sim.py`
- Sim Mode sampling with Correlation / Sim Diversity / Ownership Fade knobs → `optimizer.py`
- Late Swap auto-resim loop + Quick Swap → `late_swap.py`
- Contest Flashback (Sim ROI on real lineups) → `flashback.py`
- Custom projection CSV upload/download concept → `projections.to_csv_rows()`

## Roadmap for Next Session(s)

### P0 — Correctness
1. Real salary/position/cap rules per site (DK classic NFL 9-man with FLEX, etc.)
2. Wire `data_sources.py` fetchers into the simulator (real slates end-to-end)
3. DK contest CSV importer (entries + ownership) for Flashback validation
4. NBA minutes-redistribution model for injury slates
5. Unit tests: percentile correctness, correlation sign checks, ownership sums, quick-swap invariants

### P1 — Data Quality
1. NFL play-call/usage models trained on nflverse (validate on held-out weeks)
2. Weather integration (OpenWeather) → park/wind adjustments
3. Ownership calibration study vs post-contest CSVs (MAE reporting)
4. 13-contest heuristics validation against real contests
5. Backtest harness: predicted Sim ROI vs realized ROI over 100 slates

### P2 — Product
1. Minimal web UI (upload slate → projections/ownership/lineups tables)
2. Benchmark 100k contest sims ≤ 30s; optimize hot paths
3. GitHub Pages custom domain; CI (pytest on PR)

### Long-Term / Blocked
1. Live flagship ownership — needs opt-in network or partnership
2. Industry-aggregated projections — needs multi-source public aggregation + calibration
3. Full 18-sport coverage — per-sport models + data deals

## Irregularities Observed (for review)

- SaberSim pricing page contains "Lorem ipsum" placeholder copy in feature tooltips (2026-09-22).
- SaberSim says "USFL" on pricing optimizer list but "UFL" on homepage/projections list.
- `statsapi.mlb.com` root + docs now show login walls; API paths remain public.
- `api-web.nhle.com/` root 404s; use `/v1/...` paths.
- `rotogrinders.com/resultsdb/nfl` redirects to a premium sales page (citation removed).
- Video-transcript quotes cannot be text-verified (page HTML has no transcript).

## No Hallucination Statement

Every gap above is labeled, sourced where public info exists, and honest about what is unknown.
If you find an unsourced numeric claim, please open an issue with label `verification`.
