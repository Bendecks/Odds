# PR scope

This change addresses two production findings from feed run 7:

1. A single run replaced ~40k raw JSONL lines in Git. Raw snapshots now become 30-day compressed Actions artifacts; only compact durable state remains in Git.
2. Only 6 reference rows received Bet365 H2H prices despite broad Bet365 coverage. Exact-match diagnostics now separate event absence, query-budget exclusion and missing H2H target prices before any fuzzy matching is attempted.

It also adds a compact inventory of all observed Bet365 market families so future model expansion is evidence-led without narrowing collection.
