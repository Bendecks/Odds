# Feed health metrics

Operational health should be read from compact outputs rather than raw row count alone:

- Bet365 events available / queried
- raw observations / unique markets
- reference events / observations / book depth
- exact cross-provider event matches
- matched target H2H prices
- provider errors
- reference API quota remaining
- latest decision and model-signal ledger size

A healthy collector can still output NO BET. NO BET is a model/risk decision, not a feed failure.
