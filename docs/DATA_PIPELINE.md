# Data pipeline

The system deliberately separates observation from betting decisions.

1. **Bet365 discovery** — collect a broad football market universe from Odds-API.io. Do not discard an observation because its market, price, league or apparent edge looks unattractive.
2. **Reference observations** — collect H2H fair-probability observations from The Odds API. Draws and observations with only one or two reference books are retained and labelled with `reference_quality`.
3. **Enrichment/join** — match Bet365 target prices to reference observations where possible. Unmatched Bet365 observations remain useful discovery data.
4. **Scoring** — calculate implied probability, edge, EV and stake only after data collection.
5. **Final play gate** — only here enforce freshness, minimum reference-book count, edge, EV, minimum stake and bankroll caps.
6. **Validation** — persist decisions, capture closing odds/results, and evaluate calibration, CLV and ROI. Legacy paper history is diagnostic only and does not validate the new model.

Current reference coverage is intentionally narrower than Bet365 discovery because The Odds API free quota is scarce. This is a data-enrichment constraint, not a reason to delete or ignore the broader Bet365 universe.

GitHub Pages is display-only. Secrets and API credentials must never be shipped to browser JavaScript. Acquisition and model jobs belong in GitHub Actions or another server-side process.
