# Odds — START HERE

This is the canonical handoff for every fresh ChatGPT session. **Do not trust remembered chat status over GitHub.** Always inspect actual `main`, open PRs/branches, Actions/CI, scheduled runs, GitHub Pages and current outputs before changing anything. GitHub is the project's persistent memory between conversations.

## Mission
Build a personal autonomous value-betting assistant that discovers as many **legitimate PAPER PICKS** on Bet365 as possible across as many correctly modelled markets as possible, without lowering data-quality or value gates. Current bankroll: **50 DKK**.

The system is PAPER only. `PAPER PICK` means record and validate, never a real-money instruction. LIVE/PLAY requires robust out-of-sample evidence plus an explicit human decision. No martingale or chasing losses.

## Core rule — broad discovery, narrow final gate
Preserve broad observations and attach quality/confidence metadata. Apply edge, EV, reference quality/depth, freshness, exact Bet365 identity and staking constraints at the final gate. Fuzzy matching is diagnostic only. Actionable candidates require exact provider identity.

Do not manufacture picks by lowering edge, EV, freshness, identity or reference-quality requirements.

## Active odds-provider architecture
**Odds-API.io is the only active odds provider.** `the-odds-api.com` is legacy/inactive and must not be reintroduced into the active pipeline.

Current free bookmaker slots:
- **Bet365** = execution price.
- **Unibet** = one separate recreational reference observation.

A bootstrap snapshot collects Bet365 + Unibet. Fresh Unibet markets are de-vigged into reference probabilities. Unibet counts as **one economic reference only**. Bet365 has reference weight zero when evaluating Bet365 and must never define the fair probability against which its own price is tested.

Raw provider streams are short-retention workflow artifacts rather than permanent public history. Never commit API keys or invent prices.

## Provenance / independence semantics
Merged PR #83 introduced explicit source provenance. Reference/evidence records must distinguish:
- `transport_provider_id`
- `economic_source_id`
- `evidence_family`
- `model_or_feed_version`

The same bookmaker/economic source delivered through multiple APIs/transports counts **once**, never multiple times. Missing provenance must fail closed rather than inflate reference depth. Bet365 execution also has explicit provenance.

The existing 3-reference final gate remains fail-closed until a replacement Reference Quality Gate has been shadow-tested and shown to be defensible. Do not simply lower `min_reference_books`.

## Value policy
Read actual `config/value_policy.json` before changing it. Current conceptual policy:
- mode PAPER
- bankroll 50 DKK
- min edge 2%
- min EV 2.5%
- Kelly fraction 0.125
- max stake 3% bankroll
- max Bet365 price age 20 min
- min reference books 3
- max bets/event 1
- validation target: at least 300 decisive new-model bets plus positive ROI/CLV and acceptable calibration

Bet365 practical minimum stake is 2 DKK. During PAPER validation, a theoretical Kelly stake below 2 DKK must not suppress an otherwise qualifying observation. Before LIVE, reconcile the 2 DKK minimum with the current 3% bankroll cap (=1.50 DKK at 50 DKK).

## Deep Research — required development basis
Development must combine the conclusions of the project's research work rather than following one report in isolation.

### Research priority A — freshness / quota / identity
A major short-term bottleneck is freshness and efficient use of provider calls. Prioritize robust exact event/market identity, freshness and quota-aware collection. WebSocket/streaming freshness and adaptive polling should be evaluated where the provider/free plan actually supports them. Validate current provider documentation/limits before implementing quota assumptions.

### Research priority B — stronger independent fair probability
Do **not** add arbitrary free bookmaker feeds merely to satisfy a count of three. Target architecture from the latest research is approximately:

**Unibet no-vig + verified independent free external market price + Dixon–Coles/Elo model → calibrated ensemble → Reference Quality Gate → Bet365 execution**

Candidate research directions:
- first external PoC: API-Football/API-Sports
- secondary PoCs: SportsGameOdds, FieldFunded
- model-data candidates: Football-Data.co.uk, football-data.org, StatsBomb Open Data

Any external odds/feed PoC must verify freshness, market coverage, bookmaker/economic provenance and compatibility with the project's Odds-API.io-only active-provider rule. Keep questionable/external architectures SHADOW_ONLY until explicitly promoted.

Build a Bet365-independent football fair model using free public match data, initially **SHADOW_ONLY**. Dixon–Coles + Elo is the first model direction. Compare de-vig methods (at minimum multiplicative vs power) out-of-sample without changing production qualification until evidence supports it.

A future Reference Quality Gate may combine independent market evidence and a calibrated model, but may replace the current gate only after documented shadow validation/non-inferiority.

## Current active flow
1. `scripts/odds_api_io_bootstrap.py` collects Bet365 + Unibet and builds fresh reference candidates.
2. `scripts/odds_api_io_reference.py` de-vigs Unibet, attaches exact Bet365 prices and records provenance/economic-source identity.
3. Diagnostics preserve broad provider/market observations.
4. Derived/modelled markets are allowed only with sufficient input quality.
5. `scripts/value_decision_engine.py` applies final gates; actionable output requires verified Bet365 price, concrete Bet365 event ID and exact match method.
6. Evaluations enter `data/decision_runs.jsonl`; qualifying new-model signals enter model/closing/settlement ledgers.
7. Closing capture and settlement use exact provider identity and fail closed on ambiguity.
8. `scripts/model_validation_readiness.py` calculates ROI, CLV, Brier/calibration, ECE, bootstrap interval and version metrics.
9. De-vig shadow comparison records multiplicative-vs-power differences without changing production qualification.
10. GitHub Pages displays current decision, funnel, PAPER history, validation and development status.

## Web app
GitHub Pages: `https://bendecks.github.io/Odds/`

Top navigation now contains Handling, Funnel, Paper picks, Validering, Udvikling and Status. Udvikling has its own highlighted navigation button.

`output/development_status.json` is the living human-readable roadmap. Keep it updated after substantive milestones. The Pages workflow must explicitly publish this file; a prior bug omitted it and caused the Development module to show `-/10` / unavailable. PR #83 fixed the Pages artifact list to include it.

Keep **current decision** and **historical PAPER picks** conceptually separate in UI and data. A current `NO BET` can coexist with historical paper records; do not present historical picks as current actionable candidates.

## Important files
- `config/value_policy.json` — canonical risk/value policy
- `data/value_candidates.json` — current broad candidates; active runs replace stale legacy reference state
- `data/model_signals.jsonl` — deduplicated new-model signal ledger
- `data/decision_runs.jsonl` — evaluation/funnel diagnostics
- `data/model_settlements.jsonl` — canonical settlements
- `output/latest_decision.json` — current user-facing decision
- `output/model_validation_readiness.json` — validation state
- `output/bet365_join_status.json`, `output/reference_match_diagnostics.json`, `output/unibet_observer.json` — diagnostics
- `output/operational_status.json` — compact operational state
- `output/paper_pick_history.json` — historical PAPER history for Pages
- `output/development_status.json` — living development roadmap
- `output/devig_shadow_comparison.json` — multiplicative-vs-power no-vig shadow report
- `scripts/event_match_diagnostics.py` — conservative fuzzy diagnostic resolver
- `scripts/paper_pick_history.py` — public PAPER history builder
- `.github/workflows/` — production, CI, closing, settlement and Pages

## Last verified handoff state — 2026-09-04
Always verify GitHub again; Actions can move `main` after this handoff.

Recent milestones:
- PR #78 migrated the active candidate/reference pipeline to one Odds-API.io Bet365 + Unibet snapshot and removed stale legacy candidate reuse.
- PR #80 documented the Odds-API.io-only architecture and PAPER stake-floor semantics.
- PR #81 added the persistent Development overview to Odds Lab.
- PR #82 added sticky top navigation and a dedicated Development button.
- A manual `Odds-API.io value feed` on 2026-09-03 processed about **320 candidates**, about **278 with verified Bet365 data**, and correctly returned **NO BET** under the new architecture. Two previously visible PAPER PICKS were old pre-migration state and were not reproduced by the fresh feed.
- PR #83 added economic-source provenance/dedup regression protection and fixed Pages publication of `development_status.json`. It was squash-merged as `c191345c89f0c7e51b53a03118ff401beb39c650` after green Value Engine CI.
- After that merge, scheduled closing-price automation moved `main` to `8843afca0bd089b343be9849287e0ebaa88c3187` (`Update model closing prices`). This illustrates why a fresh session must inspect actual current state before branching.
- PR #85 added a central Odds-API.io quota budget guard for feed, closing and settlement workflows. It was squash-merged as `edc1f3010836635f110350079824d2235aed2c74`; subsequent scheduled automation moved `main` again.
- PR #86 began de-vig shadow comparison. Production fair probabilities remain multiplicative no-vig; power no-vig is recorded only as shadow metadata/reporting and must not affect current picks until validated.

Historical PAPER records may still exist from older architecture. They are useful only as clearly labelled history and do **not** validate the current model. Validation requires genuine future new-model signals and exact settlements.

## Next development sequence
Use evidence and actual current diagnostics to adjust order, but the intended sequence is:
1. Verify current main/CI/Pages/production and confirm Development module is actually populated after the Pages fix.
2. Keep provenance/economic-source dedup enforced everywhere new evidence enters.
3. Keep the central quota guard healthy and inspect real quota output after scheduled runs.
4. Improve freshness and exact event/market identity; evaluate adaptive/streaming collection if supported.
5. Continue **de-vig shadow comparison** and evaluate multiplicative vs power out-of-sample.
6. Research/test the first defensible independent external reference PoC without weakening provider-independence rules.
7. Build Dixon–Coles + Elo on free public match data in SHADOW_ONLY.
8. Calibrate/ensemble independent signals and measure out-of-sample performance.
9. Shadow-test a Reference Quality Gate; production promotion only after evidence of non-inferiority/benefit.
10. Expand legitimate market breadth: 1X2 → DNB/double chance, goal model → totals/BTTS, then handicaps only with correct semantics.
11. Accumulate at least 300 decisive current-model PAPER bets with exact closing/settlement evidence before considering LIVE.

## What the user should be asked to do
Work autonomously by default. Ask the user only for genuine external blockers, for example:
- create/provide a free API account/key when a chosen PoC requires it;
- manually run a GitHub Action when production verification genuinely requires a real feed run;
- report/screenshoot a UI problem that cannot be reproduced from repository/deployment state.

Do not ask the user to make routine code changes. Do not ask them to place real bets during PAPER validation. Do not ask them to add bankroll merely to work around the 2 DKK minimum.

## Required behavior for fresh ChatGPT sessions
When the user says `Fortsæt`, perform actual safe work rather than only describing a plan. Start from actual latest `main`; inspect open PRs/branches and Actions; branch; implement; add tests; open PR; inspect CI; fix failures; merge only when safe; verify post-merge state/deployment; update `output/development_status.json` and this handoff when architecture/strategy materially changes.

GitHub is the persistent project memory. This document is the map; repository state and Actions are authoritative.
