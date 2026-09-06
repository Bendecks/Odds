# API-Football external reference PoC

Generated: 2026-09-06T19:49:47Z
Mode: SHADOW_ONLY
Production impact: none
Configured: True
OK: True

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

### /status
- configured: True
- ok: True
- status_code: 200
- results: 0
- headers:
```json
{
  "x-ratelimit-requests-limit": "100",
  "x-ratelimit-requests-remaining": "99",
  "x-ratelimit-limit": "10",
  "x-ratelimit-remaining": "9"
}
```

### /odds/bookmakers
- configured: True
- ok: True
- status_code: 200
- results: 33
- headers:
```json
{
  "x-ratelimit-requests-limit": "100",
  "x-ratelimit-requests-remaining": "97",
  "x-ratelimit-limit": "10",
  "x-ratelimit-remaining": "8"
}
```

### /odds/bets
- configured: True
- ok: True
- status_code: 200
- results: 338
- headers:
```json
{
  "x-ratelimit-requests-limit": "100",
  "x-ratelimit-requests-remaining": "96",
  "x-ratelimit-limit": "10",
  "x-ratelimit-remaining": "7"
}
```
