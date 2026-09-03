# Odds — START HERE

This file is the canonical handoff for a fresh ChatGPT session. Do not trust remembered chat status over GitHub. Always inspect actual `main`, open PRs/branches, Actions runs and production outputs first.

## Mission
Build a personal autonomous value-betting assistant. The machine must discover opportunities, estimate fair probability, verify the actual Bet365 price, decide whether a candidate qualifies and calculate a theoretical stake. Current bankroll is **50 DKK**.

The system is **PAPER only** while it accumulates out-of-sample evidence. `PAPER PICK` means record and validate; it is not an instruction to place a real bet. LIVE/PLAY promotion requires robust evidence plus an explicit human decision.

No profit guarantee. Never use martingale or chase losses.

## Core design rule: broad discovery, narrow final gate
Do not aggressively filter discovery. Preserve observations and attach quality/confidence metadata. Edge, EV, reference quality/depth, freshness, exact Bet365 identity and staking constraints belong at the final decision gate.

Fuzzy event matching is diagnostic/prioritization only. It must never set `bet365_verified` or cross the PAPER PICK/PLAY boundary. Actionable candidates require explicit exact provider identity.

## Active provider architecture
The active odds pipeline uses **Odds-API.io only**.

### Odds-API.io
- Official site: `odds-api.io`
- Base: `https://api.odds-api.io/v3`
- GitHub secret: `ODDS_API_IO_KEY`
- Current free bookmaker slots: **Bet365 + Unibet**.
- Bet365 is the execution-price source.
- Unibet is a separate recreational reference observation.
- A single bootstrap snapshot collects Bet365 + Unibet so reference construction does not require a second odds request.
- Raw Bet365 and Unibet observations are archived as limited-retention workflow artifacts rather than permanent public history.
- Relevant documented endpoints include `/sports`, `/bookmakers`, `/events`, `/odds`, `/odds/multi`, `/value-bets`, `/arbitrage-bets` and `/dropping-odds`.
- `/odds/multi` supports up to 10 event IDs per request.
- For settlement prefer explicit regulation/full-time `scores.periods.ft`; ambiguous knockout scores fail closed.

### Reference semantics
Fresh Unibet markets are de-vigged into reference probabilities. **Unibet counts as one reference book only.** It must not be duplicated or otherwise represented as multiple independent sources. The existing final requirement of at least three reference books therefore remains fail-closed for these candidates.

Bet365 execution odds must not be used to define a fair probability and then be evaluated against themselves.

The project currently needs a defensible additional independent probability/reference architecture before the normal 3-reference final gate can produce PAPER PICKs from the Odds-API.io-only setup. Do not lower that gate merely to manufacture picks.

### Legacy provider code
`the-odds-api.com` is no longer part of the active scheduled/manual odds pipeline. Historical scripts, tests or generated data referring to The Odds API may remain temporarily during staged cleanup, but they must not be treated as fresh active reference data. Active runs replace legacy candidate state rather than silently reusing it.

Never commit API keys. Never invent Bet365 odds.

## Current value policy
Canonical policy lives in `config/value_policy.json`; read the actual file before changing it. Current conceptual policy:
- mode: PAPER
- bankroll: 50 DKK
- min edge: 2%
- min EV: 2.5%
- Kelly fraction: 0.125
- max stake: 3% bankroll
- max Bet365 price age: 20 minutes
- min reference books for final qualification: 3
- max bets per event: 1
- validation target: at least 300 decisive new-model bets plus positive ROI and positive CLV requirements

Bet365's practical real-money minimum stake is 2 DKK. During PAPER validation, a small theoretical Kelly stake must not suppress otherwise qualifying PAPER observations. This exception does not relax edge, EV, identity, freshness or reference-quality gates. Before any future LIVE mode, the 2 DKK practical minimum must be reconciled explicitly with the current 3% bankroll cap (1.50 DKK at a 50 DKK bankroll).

Do not reuse legacy staking such as `max(10, round(edge_pct*4))`.

## Current architecture
Main active flow:
1. `scripts/odds_api_io_bootstrap.py` collects the Bet365 + Unibet Odds-API.io snapshot, builds fresh Unibet no-vig reference candidates and attaches exact Bet365 execution prices from the same observation set.
2. Provider-schema and market diagnostics preserve broad observations.
3. Derived-model scripts may add modelled markets only when their input-quality requirements are met.
4. `scripts/value_decision_engine.py` applies final safety/value gates. Actionable output requires verified Bet365 price + concrete Bet365 event ID + `event_match_method == exact`.
5. Every evaluation is recorded in the decision-run ledger.
6. Actionable new-model signals feed closing-price and settlement queues.
7. Closing capture and settlement use exact provider identity; settlement uses regulation full-time semantics and fails closed on ambiguity.
8. `scripts/model_validation_readiness.py` calculates ROI, CLV, Brier/calibration, ECE, bootstrap ROI interval and model-version metrics. Promotion remains false until explicitly decided.
9. GitHub Pages displays current decision, validation progress and PAPER PICK history.

## Important files
- `config/value_policy.json` — risk/value policy.
- `data/value_candidates.json` — current broad reference candidates with any exact Bet365 joins; active runs must not preserve stale legacy reference probabilities.
- `data/model_signals.jsonl` — deduplicated new-model signal ledger.
- `data/decision_runs.jsonl` — evaluation/funnel diagnostics.
- `data/model_settlements.jsonl` — canonical new-model settlements.
- `output/latest_decision.json` — current user-facing decision.
- `output/model_validation_readiness.json` — validation state.
- `output/bet365_join_status.json`, `output/reference_match_diagnostics.json`, `output/unibet_observer.json` — provider/reference diagnostics.
- `scripts/event_match_diagnostics.py` — conservative fuzzy diagnostic resolver.
- `scripts/paper_pick_history.py` — compact public PAPER history for Pages.
- `.github/workflows/` — production schedules, CI, closing capture, settlement and Pages.

## Web app
GitHub Pages: `https://bendecks.github.io/Odds/`

The dashboard exposes compact canonical state, not API keys or raw provider snapshots.

## Last verified development state at this handoff
On 2026-09-03 PR #78, **Bootstrap reference and execution prices from Odds-API.io**, passed Value Engine CI run #213 and was squash-merged as `54c224d215690f4ac1275bcab590d534b9b3c997`.

PR #78 completed the active migration away from legacy The Odds API candidate state: one Odds-API.io snapshot collects Bet365 + Unibet, raw streams are separately archived, fresh Unibet no-vig reference candidates replace stale legacy candidates, and exact Bet365 execution prices are attached without a second provider odds request.

The principal current blocker to legitimate PAPER PICK production is now reference strength rather than provider migration: with Bet365 reserved for execution and Unibet counting honestly as one independent recreational reference, the existing 3-book final reference gate remains unsatisfied.

Do not lower edge/EV/reference/identity/freshness safety thresholds merely to manufacture PAPER PICKs.

## Known caveats
- GitHub Actions state commits can move `main`; always fetch current state before branching.
- Do not manually trigger provider workflows merely to test code when unit/CI tests suffice. Preserve quota and wait for scheduled production runs unless real production verification is justified.
- Signal-ledger deduplication means its row count is not evaluation count; use `data/decision_runs.jsonl` for operational diagnostics.
- Legacy historical betting results do not validate the new model.
- `data/bankroll.csv` is legacy and must not redefine the new 50 DKK bankroll.
- Public repo: secrets must only live in GitHub Actions secrets.

## Next priorities for a fresh session
1. Inspect actual GitHub and Actions state first.
2. Find and consume the requested Deep Research on a **100% free fair-probability/reference architecture** when it becomes available. Evaluate free supplemental non-odds data sources only when they do not reactivate a second paid odds provider or weaken independence semantics.
3. Build the strongest defensible independent probability/reference layer possible while keeping Odds-API.io as the only active odds provider.
4. Maximize candidate breadth and exact Bet365 coverage without lowering edge, EV, freshness, exact-identity or reference-quality gates.
5. Add tests before integrating any new reference/model source. Keep provenance explicit so model probabilities are not mislabeled as bookmaker consensus.
6. Accumulate genuine future PAPER PICKs and exact settlements. Do not claim empirical validation before the data exists.

## Required behavior for ChatGPT sessions
Work autonomously. When the user says `Fortsæt`, make actual safe changes and take as many consecutive steps as possible without waiting for confirmation. Branch from actual latest `main`, add tests, open PR, inspect CI, fix failures, merge only when green, and verify post-merge state/deployment. Stop only for a genuine blocker requiring user input.

Do not replace actual GitHub inspection with this document. This document is a map; the repository and Actions state are authoritative.
