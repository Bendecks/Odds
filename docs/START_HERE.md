# Odds — START HERE

This file is the canonical handoff for a fresh ChatGPT session. Do not trust a remembered chat status over GitHub. Always inspect the actual current `main`, open PRs/branches, Actions runs and production outputs first.

## Mission
Build a personal, autonomous value-betting assistant. The machine—not the user—must discover opportunities, estimate fair probability, verify the actual Bet365 price, decide whether a bet qualifies, and calculate the stake. Start bankroll for the new model is **50 DKK**.

The system is **PAPER only** while it accumulates out-of-sample evidence. `PAPER PICK` means record and validate; the user should not place it. `PLAY` must not be enabled automatically just because thresholds are crossed. LIVE promotion requires robust evidence plus an explicit human decision.

No profit guarantee. Never use martingale or chase losses.

## Core design rule: broad discovery, narrow final gate
Do not filter the universe aggressively during discovery. Preserve observations and attach quality/confidence metadata. Edge, EV, reference depth, freshness, exact Bet365 identity and staking constraints belong at the final decision gate. It should be possible for hundreds of events to produce many candidates before final qualification.

Fuzzy event matching is diagnostic/prioritization only. It must **never** set `bet365_verified` and must never cross the PAPER PICK/PLAY boundary. Final actionable candidates require explicit exact provider identity.

## Data providers
There are two different APIs and both are intentional.

### Odds-API.io — Bet365 execution-price source
- Official site: `odds-api.io`
- Base: `https://api.odds-api.io/v3`
- GitHub secret: `ODDS_API_IO_KEY`
- Authentication: `?apiKey=...`
- Used for the real Bet365 event/market/price and exact closing/result data.
- Relevant official endpoints: `/sports`, `/bookmakers`, `/events`, `/odds`, `/odds/multi`, `/value-bets`, `/arbitrage-bets`, `/dropping-odds`.
- `/odds/multi` supports up to 10 event IDs per request. PR #37 introduced batching while preserving per-event fallback.
- Official docs supplied by user: `https://docs.odds-api.io/llms-full.txt`; OpenAPI: `https://docs.odds-api.io/api-reference/openapi.json`.
- Official score semantics: prefer explicit regulation/full-time period (`scores.periods.ft`) for H2H settlement. Do not settle a knockout from an ambiguous top-level score that may include extra time/penalties.

### The Odds API — independent reference consensus
- Service: `the-odds-api.com`
- GitHub secret: `THE_ODDS_API_KEY`
- Used as reference-market consensus, not as the Bet365 execution source.
- Reference bookmaker keys currently include Pinnacle, Betfair Exchange EU, Betsson, NordicBet and William Hill where offered.
- `/v4/sports` is quota-free. Paid odds requests are deliberately rotated across active soccer competitions to preserve broad coverage within quota.

Never commit either API key. Never invent Bet365 odds.

## Current value policy
Canonical policy lives in `config/value_policy.json`. At handoff it is conceptually:
- mode: PAPER
- bankroll: 50 DKK
- min edge: 2%
- min EV: 2.5%
- Kelly fraction: 0.125
- max stake: 3% bankroll
- min stake: 1 DKK
- max Bet365 price age: 20 minutes
- min reference books for final play: 3
- max bets per event: 1
- validation target: at least 300 decisive new-model bets, positive ROI threshold and positive CLV requirement

Read the actual config before changing anything. Do not reuse legacy staking such as `max(10, round(edge_pct*4))`; it is incompatible with a 50 DKK bankroll.

## Current architecture
Main flow:
1. `scripts/the_odds_feed.py` discovers active soccer reference markets and produces broad reference candidates.
2. `scripts/odds_api_io_bet365.py` discovers the Bet365 universe, preserves broad raw market observations, resolves events and attaches prices only for exact matches. It batches up to 10 event IDs per Odds-API.io `/odds/multi` request and falls back selectively to `/odds` when needed.
3. `scripts/value_decision_engine.py` applies the final safety/value/staking gates. Actionable output requires verified Bet365 price + concrete Bet365 event ID + `event_match_method == exact`.
4. Every evaluation is recorded in the decision-run ledger; repeated identical NO BETs must not disappear from operational diagnostics.
5. Actionable new-model signals feed closing-price and settlement queues.
6. Closing prices are captured using exact Bet365 identity. CLV uses the canonical original signal odds, not a copied closing-row taken price.
7. Settlement uses exact identity and regulation full-time score semantics. Ambiguous knockout scores fail closed.
8. `scripts/model_validation_readiness.py` calculates new-model ROI, CLV, Brier/calibration, ECE, bootstrap ROI interval and model-version metrics. Promotion remains false until explicitly decided.
9. GitHub Pages displays the current decision, validation progress and PAPER PICK history.

## Important files
- `config/value_policy.json` — current risk/value policy.
- `data/value_candidates.json` — current broad reference candidates with any exact Bet365 joins.
- `data/model_signals.jsonl` — deduplicated new-model signal ledger.
- `data/decision_runs.jsonl` — every model evaluation / funnel diagnostics.
- `data/model_settlements.jsonl` — canonical new-model settlements.
- closing-price ledger/queue files under `data/` — inspect current names before editing.
- `output/latest_decision.json` — current user-facing decision.
- `output/model_validation_readiness.json` — new-model validation state.
- `output/bet365_join_status.json` and `output/reference_match_diagnostics.json` — provider/join diagnostics.
- `scripts/event_match_diagnostics.py` — conservative fuzzy diagnostic resolver.
- `scripts/paper_pick_history.py` — compact public PAPER history for Pages.
- `.github/workflows/` — production schedules, CI, closing capture, settlement and Pages.

Raw Bet365 observations are intentionally not permanent public history. Raw snapshots belong in workflow artifacts with limited retention; compact canonical ledgers belong in Git.

## Web app
GitHub Pages: `https://bendecks.github.io/Odds/`

The dashboard shows the latest action plus PAPER PICK history. The public history is generated from canonical signal/settlement/closing ledgers and exposes up to 100 recent paper picks with odds, stake, edge, result, CLV and P/L. It must not expose API keys or raw provider snapshots.

## Last verified development state at this handoff
PR #37 **Batch Odds-API.io Bet365 requests** passed CI and was squash-merged to `main` as commit `bebe82bde84481fa3a4236288e3092a1158136e6` on 2026-08-31. It changed broad Bet365 collection from roughly 80 individual `/odds` calls to normally ~8 `/odds/multi` batches for the same 80-event breadth, with selective individual fallback. Do not assume this SHA remains current: scheduled workflows can commit state after this file is written.

Immediately before PR #37, PR #36 added PAPER PICK history to Pages and both post-merge CI and Pages deployment succeeded.

Latest inspected decision-run before PR #37 had 45 reference candidate rows with fair probabilities and only 3 exact Bet365-verified rows. The principal observed funnel bottleneck was therefore exact Bet365/reference coverage, not lack of reference candidates. Latest decision was still `NO BET`; there had not yet been a new-model PAPER PICK at that inspection.

Do not lower edge/EV/safety thresholds merely to manufacture PAPER PICKs.

## Recent safety/infrastructure milestones
- Broad Bet365 candidate universe and compact raw observation layer.
- Broad reference H2H preservation including draws and low-depth observations as metadata.
- Conservative fuzzy event resolver, diagnostic only.
- Dynamic active-soccer discovery and quota-aware rotating reference coverage.
- New-model settlement queue and hardened canonical settlement schema.
- Exact Bet365 closing-price capture.
- ROI bootstrap uncertainty, model-version metrics, Brier/ECE calibration diagnostics.
- Provider rate-limit degradation and fail-safe attempted-call accounting.
- Exact provider event identity propagated through signal/closing/settlement pipeline.
- Regulation-time settlement safety for extra time/penalties.
- Final decision requires exact Bet365 identity explicitly.
- PAPER PICK history deployed to Pages.
- Odds-API.io Bet365 requests batched via `/odds/multi` with selective fallback.

## Known caveats
- GitHub Actions state commits can move `main`; always fetch current state before branching.
- Do not manually trigger provider workflows merely to test code when unit/CI tests suffice. Preserve quotas and wait for scheduled production runs unless a real production verification is justified.
- The Odds API reference quota is finite; keep paid per-run requests bounded and rotating.
- Signal ledger deduplication means its row count is not the same as number of evaluations; use `data/decision_runs.jsonl` for operational run count.
- Legacy historical betting results do not validate the new model. New-model OOS settlements are what matter.
- `data/bankroll.csv` is legacy and must not redefine the new 50 DKK bankroll.
- Public repo: secrets must only live in GitHub Actions secrets.

## Next priorities for a fresh session
First inspect actual GitHub state and scheduled runs. Then, unless newer evidence changes priorities:
1. Verify the first scheduled production feed after PR #37: batch/fallback counters, provider attempts, observations, exact matches, decision, and absence of regressions. Do not trigger an extra provider run just for curiosity.
2. Diagnose the complete decision funnel from `decision_runs`, candidates and provider diagnostics: reference rows → exact event matches → fresh Bet365 prices → >=3 reference books → fair probability → edge → EV → Kelly/minimum-stake gate.
3. Use the lower Odds-API.io request count to improve **breadth of exact Bet365 verification**, not to loosen final betting rules. Respect provider-plan limits discovered from current official docs.
4. Consider Odds-API.io `/value-bets?bookmaker=Bet365` only as a diagnostic/secondary signal at first. Do not let it silently replace the independent reference model or final exact-price safety gate.
5. Consider odds movements / WebSocket only after the REST pipeline is stable and only if they materially improve freshness/closing capture without complicating validation.
6. Improve dashboard operational visibility (evaluation count/funnel/provider health) if useful, without exposing raw/private data.
7. Accumulate genuine future PAPER PICKs and exact settlements. Do not claim empirical validation before the data exists.

## Required behavior for ChatGPT sessions
Work autonomously. When the user says `Fortsæt`, make actual safe changes and take as many consecutive steps as possible without waiting for confirmation. Branch from the actual latest `main`, add tests, open PR, inspect CI, fix failures, merge only when green, and verify post-merge state/deployment. Stop only for a genuine blocker requiring user input.

Do not replace actual GitHub inspection with this document. This document is a map; the repository and Actions state are authoritative.
