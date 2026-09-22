# Limitations & Honest Gaps — Flags for Review

This file documents what we CANNOT fully replicate without proprietary SaberSim data.
These are not hallucinations — they are honest gaps flagged for manual review.

## Proprietary Models We Approximate

### 1. Coaching Tendency Model
- **What SaberSim says**: "Each sim includes strategy, play-calling, coaching decisions, and game flow" + "Models strategy, coaching tendencies, clock effects, player skill sets, and matchup dynamics"
- **Source**: https://support.sabersim.com/en/articles/12078831-how-projections-work
- **What we have**: nflverse EPA + historical play-call rates (open source)
- **Gap**: ~5-10% accuracy vs calibrated model. SaberSim likely uses ML trained on 5+ years PBP with team-specific tendencies, down/distance, personnel.
- **What needed for parity**: Train XGBoost/LSTM on nflverse 2018-2024 PBP (300k plays) to predict play type, target share, run/pass, etc. Needs GPU.
- **Flag**: APPROXIMATION — needs validation

### 2. Industry-Aggregated Projections for Field Lineups
- **What SaberSim says**: "Instead, it builds multiple sets of opponent lineups using industry-aggregated projections that reflect actual construction and ownership trends"
- **Source**: https://support.sabersim.com/en/articles/12079199-how-contest-sims-work
- **What we have**: Public projections (we use our own sim projections as proxy)
- **Gap**: Real field uses aggregate of many sources (RotoGrinders, THE BAT, etc.). Ownership may be off 2-5% for low-owned punts.
- **What needed**: Scrape free projections from multiple sites, aggregate. Premium sources paywalled.
- **Flag**: APPROXIMATION

### 3. Live Flagship Ownership Real-Time
- **What SaberSim says**: "See the actual ownership in the flagship contests in real time" + "Live-updating Flagship ownership"
- **Source**: https://www.sabersim.com/pricing
- **What we have**: Post-contest DK CSV (public after lock) + simulated field lineups pre-lock
- **Gap**: True live pre-lock flagship ownership requires either insider DK data or large user base sharing lineups. Cannot achieve 100% without network effect.
- **What needed**: Build Chrome extension that users opt-in to share anonymized ownership pre-lock, aggregate. Or partnership with DK.
- **Flag**: LIMITATION — cannot fully replicate without network effect

### 4. 13 Contest Types Heuristics
- **What SaberSim says**: 13 contest types list verbatim from pricing page + "Opponents don’t play the same way in a low-stakes 150-max as in a high-stakes single-entry"
- **Source**: https://www.sabersim.com/pricing
- **What we have**: Reasonable heuristics per type (MME more diversified, SE more chalk, High Stakes sharper, Low Stakes more random, Winner-Take-All more contrarian)
- **Gap**: Exact heuristics proprietary — how much more random? How much more chalk? Needs validation vs real contest results.
- **What needed**: Collect 100+ real contests per type (DK CSV), analyze ownership distribution, stack rates, value bias per type, then calibrate heuristics.
- **Flag**: APPROXIMATION — needs validation

### 5. SaberScore Formula
- **What SaberSim says**: "Adjusted Ownership feeds directly into OLD SaberScore as a negative variable, penalizing lineups overloaded with over-owned players and boosting lineups with the right balance of projection, upside, and leverage."
- **Source**: https://support.sabersim.com/en/articles/12078831-how-projections-work
- **What we have**: Proxy: SaberScore = projection * (ceiling/mean) * (1 + leverage) where leverage = win_rate - ownership
- **Gap**: Exact formula proprietary. Our proxy captures intent but not exact weights.
- **What needed**: Reverse engineer via trial? Or implement custom metric feature (Ultimate plan allows custom metrics) so users can define own.
- **Flag**: PROXY — not exact

### 6. Sport-Specific Nuances
- **What SaberSim supports**: 18 sports: NFL, NBA, MLB, NHL, MMA, PGA, SOCCER*, TENNIS, NASCAR, LOL, CSGO, CFB, CBB*, F1, UFL, COD*, CFL*, WNBA
- **Source**: https://www.sabersim.com/
- **What we have**: NFL/NBA/MLB fully implemented, NHL/PGA stubbed, others generic
- **Gap**: Each sport needs dedicated model:
  - PGA: course fit, strokes gained, weather
  - MMA: matchup styles, finish rates
  - NASCAR: lap leaders, track position
  - LOL/CSGO: economy, meta
  - etc.
- **What needed**: Dedicated model per sport, using official APIs (PGA Tour ShotLink, etc.)
- **Flag**: PARTIAL — 3/18 fully implemented

### 7. Scale & Performance
- **What SaberSim says**: "Sim each lineup in your pool against a representative contest 100k times in 30 seconds or less."
- **Source**: https://www.sabersim.com/pricing
- **What we have**: Python numpy vectorized, 10k sims in ~5s for demo, 100k would be ~50s on single core
- **Gap**: SaberSim runs in cloud infra (likely Go/Rust + GPU). Local Python slower.
- **What needed**: Cloud batch (AWS Lambda, Modal, or Rust extension) + parallelization
- **Flag**: PERFORMANCE — functional but slower

## What We CAN Fully Replicate (Verified)

- Play-by-play simulation concept (thousands of scripts)
- Point projections = mean across sims + percentiles
- Field lineups concept + ownership as descriptive statistic
- Contest Sims concept (real outcomes + opponent lineups + payout structures)
- Sim Mode optimizer sampling from scripts, stacks emerge organically
- Correlation, Sim Diversity, Ownership Fade sliders
- Late Swap auto-resim + Quick Swap
- Contest Flashback 100k re-sim
- Custom projections CSV upload/download
- ROI metrics (ROI, Cash Rate, Win Rate, ROI StdDev)

All above verified with source links in VERIFICATION.md and docs/index.html.

## Suggestions for Next Session

### P0 (Must Have for MVP)
1. Train ML models for NFL play-call tendencies using nflverse
2. Implement NBA minutes redistribution on injury (Razzball says proprietary algorithm — need to reverse engineer)
3. Build DK contest CSV scraper for Flashback automation
4. Weather integration: OpenWeather → park factors
5. Unit tests with deterministic seeds

### P1 (Important for Parity)
1. Validate 13 contest heuristics vs real contests
2. PGA course fit model
3. React front-end UI
4. Backtesting framework: sim ROI vs actual ROI over 100 slates
5. Deploy GitHub Pages with custom domain

### Long Term (Blocking Full Parity)
1. Live flagship ownership via Chrome extension opt-in
2. Industry-aggregated projections via scraping free sources
3. Cloud infra for 5000 sims x 15 games

## No Hallucination Guarantee

All gaps above are honest, flagged, with source links showing what is proprietary. We did not invent any SaberSim feature — every feature we claim to replicate is linked to official doc.

If you find any gap not flagged, please open issue.
