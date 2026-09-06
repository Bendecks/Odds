# API-Football external reference PoC

Generated: 2026-09-06T18:38:15Z
Mode: SHADOW_ONLY
Production impact: none
Configured: False
OK: False

This probe is only for evaluating API-Football/API-Sports as a future independent external market reference.
It must not change PAPER PICK qualification until freshness, coverage and provenance are validated.

## Provenance contract
```json
{
  "transport_provider_id": "api-sports:api-football",
  "economic_source_id": "api-football:bookmaker:<bookmaker_id>",
  "evidence_family": "external_market_price",
  "model_or_feed_version": "api-football-poc-v1"
}
```

## Required before promotion
- API key configured
- bookmaker ids observable
- target markets observable
- fresh pre-match odds for same events as Bet365 candidates
- economic_source_id mapped per bookmaker

## Endpoint probes

### credentials
- configured: False
- ok: False
- status_code: None
- results: None
- errors:
```json
"Missing one of API_FOOTBALL_KEY, APISPORTS_KEY in GitHub Secrets."
```
