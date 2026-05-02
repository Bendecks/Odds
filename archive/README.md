# Archive

This folder records files archived during cleanup. The original file contents remain recoverable through Git history.

Cleanup mode: A — safe archive, no production pipeline files removed.

## Active production files kept

- `scripts/v6_expansion_engine.py`
- `scripts/paper_tracker.py`
- `scripts/paper_auto_settler.py`
- `scripts/email_reporter.py`
- `scripts/v9_performance_feedback.py`
- `.github/workflows/v6_expansion_engine.yml`
- `.github/workflows/paper_tracker.yml`
- `.github/workflows/paper_settler.yml`
- `.github/workflows/email_reporter.yml`
- `.github/workflows/v9_feedback.yml`

## Archived/removed from root

### Old engines
- `scripts/data_hunter_v2.py`
- `scripts/v4_market_engine.py`

### Old probes
- `scripts/odds_api_io_probe.py`

### Superseded manual settlement
- `scripts/paper_settler.py`

### Old workflows
- `.github/workflows/data_hunter_v2.yml`
- `.github/workflows/v4_market_engine.yml`
- `.github/workflows/odds_api_io_probe.yml`

### Old probe outputs
- `output/odds_api_io_probe.md`
- `output/odds_api_io_probe.json`

Notes: These files are not used by the current autonomous pipeline. They were removed from the active tree to prevent old scheduled actions or old scripts from confusing the live system.
