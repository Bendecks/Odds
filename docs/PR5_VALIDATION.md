# Validation criteria

Before merge:
- unit tests green;
- raw JSONL absent from Git diff except deletion;
- workflow uploads raw JSONL as artifact;
- workflow commits compact reports and ledgers;
- join remains exact/safe while diagnostics are gathered.

After merge, one feed run should verify:
- artifact exists;
- commit is small relative to prior ~40k-line snapshot replacement;
- `reference_match_diagnostics.json` explains the six-match bottleneck;
- market inventory is populated from the same raw snapshot before archival.
