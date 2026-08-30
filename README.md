# Odds Lab

Personal value-betting research and recommendation dashboard.

## Product contract

The normal user flow must require no modelling decisions. The system owns candidate discovery, probability estimation, value gates, ranking and stake sizing. The user-facing output is either:

- `PLAY` — event, exact market/pick, minimum acceptable odds and exact stake; or
- `NO BET` — no qualified opportunity.

Initial bankroll: **50 DKK**.

## Validation contract

Real-money recommendations remain disabled until the underlying strategy has adequate out-of-sample evidence. Track every signal with timestamp/model version, offered odds, fair probability, closing odds, result, profit/loss, CLV and bankroll. Evaluate calibration, CLV, ROI/yield, drawdown and sample size. Never use martingale or loss chasing.

## GitHub Pages

The root `index.html` is a static mobile-first dashboard suitable for GitHub Pages. Data/model automation will be added through generated static data artifacts and GitHub Actions so the Pages UI can remain simple.
