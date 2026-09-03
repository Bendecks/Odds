# Odds-API.io quota policy

Odds-API.io is the only active odds provider. Bet365 discovery must stay broad, but scheduled feed, closing capture and settlement jobs share the same provider budget.

Current policy:
- Bet365/Odds-API.io discovery remains broad.
- `scripts/odds_api_io_quota_budget.py` is the central budget guard for provider-call caps.
- The guard reads `output/api_quota_status.json` when quota headers are available, applies a role-specific reserve, and writes the allowed cap into the workflow environment.
- If Odds-API.io does not expose a usable remaining-quota header, the guard keeps the existing conservative workflow cap instead of guessing a false limit.
- Weak one/two-book reference observations are retained as data but cannot pass the final play gate.
- Additional markets, more frequent polling or new external reference probes should be enabled only after the central guard shows enough reserve.
- Never silently exhaust monthly quota to increase apparent candidate count.
