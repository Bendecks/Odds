# Signal ledger

`data/model_signals.jsonl` is the bounded longitudinal ledger for decisions produced by the new value engine. It is separate from legacy `output/paper_bets.json`.

Each future actionable row should preserve event, market, pick, model version, Bet365 price and timestamp, reference probability/depth, stake and decision. Settlement fields will later add result, profit and closing-line information.

Do not use legacy results to promote this model to LIVE.
