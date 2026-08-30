# Storage policy

Commit durable, compact state to Git: decisions, model-signal ledger, collection snapshots, coverage reports, quota status and validation summaries.

Do not commit replace-in-place raw bookmaker snapshots. Archive them as short-retention workflow artifacts instead.

A raw snapshot is evidence for debugging/research; a compact signal/settlement ledger is the durable dataset for evaluating the betting model.
