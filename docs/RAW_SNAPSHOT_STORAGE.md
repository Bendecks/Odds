# Raw snapshot storage

`data/bet365_observations.jsonl` is generated during each feed run and is intentionally not committed to Git.

The raw snapshot is uploaded as a compressed GitHub Actions artifact with 30-day retention. Compact summaries, longitudinal collection counts, model signals and decisions remain committed to the repository.

This prevents each scheduled run from adding tens of thousands of replaced JSONL lines to Git history while preserving recent raw observations for debugging and model development.
