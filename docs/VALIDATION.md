# Validation gate

The engine must not label a recommendation as ready for real-money execution merely because a single model estimate shows positive EV.

## Required evidence
- chronological / walk-forward out-of-sample evaluation
- no leakage from closing prices or final results into pre-match features
- tracked offered odds and closing odds for CLV
- calibration metrics (Brier score and probability buckets)
- ROI/yield with uncertainty, segmented by sport/league/market/odds bucket
- minimum sample threshold before promotion from PAPER to LIVE
- model version frozen per pick

## Decision contract
The user-facing output remains only `PLAY` with event, pick, minimum acceptable odds and stake, or `NO BET`.

Current state: PAPER. No positive ROI claim is made until the evidence above supports it.
