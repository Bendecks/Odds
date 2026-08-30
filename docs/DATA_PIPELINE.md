# Data pipeline

1. Acquire current market candidates from an approved data source.
2. Normalize event, market, selection, bookmaker and timestamp.
3. Estimate fair probability independently of the target bookmaker price.
4. Pass candidates to `scripts/value_decision_engine.py`.
5. Persist every candidate and decision before event start.
6. Capture closing odds and settle results after event completion.
7. Feed outcomes into calibration, CLV and ROI reports.

GitHub Pages is display-only. Secrets and paid API credentials must never be shipped to browser JavaScript. Acquisition/model jobs belong in GitHub Actions or another server-side process.

The remaining external dependency is a reliable current odds/data source. Until that is connected, `output/latest_decision.json` correctly remains `NO BET`.
