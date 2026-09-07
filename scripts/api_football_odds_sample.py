import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone


OUT = pathlib.Path("output")
CANDIDATES = pathlib.Path("data/value_candidates.json")
STATUS_JSON = OUT / "api_football_odds_sample.json"
STATUS_MD = OUT / "api_football_odds_sample.md"
BASE_URL = "https://v3.football.api-sports.io"
SECRET_NAMES = ("API_FOOTBALL_KEY", "APISPORTS_KEY")
SAMPLE_VERSION = "api-football-odds-sample-v1"
MAX_ODDS_CALLS = int(os.getenv("API_FOOTBALL_SAMPLE_MAX_CALLS", "4"))

PREFERRED_BOOKMAKERS = ("pinnacle", "betfair", "marathonbet", "1xbet", "betway", "william hill")
EXCLUDED_BOOKMAKERS = ("bet365", "unibet")
TARGET_BETS = {
    "h2h": ("match winner", "home/away"),
    "totals": ("goals over/under", "over/under", "total goals"),
    "btts": ("both teams score", "both teams to score"),
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def api_key():
    for name in SECRET_NAMES:
        value = os.getenv(name, "").strip()
        if value:
            return name, value
    return None, ""


def endpoint_url(path, params=None):
    query = urllib.parse.urlencode(params or {})
    return f"{BASE_URL}{path}" + (f"?{query}" if query else "")


def safe_headers(headers):
    wanted = (
        "x-ratelimit-requests-limit",
        "x-ratelimit-requests-remaining",
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "retry-after",
    )
    lower = {str(k).lower(): str(v) for k, v in dict(headers).items()}
    return {key: lower[key] for key in wanted if key in lower}


def has_api_errors(body):
    errors = body.get("errors") if isinstance(body, dict) else None
    if isinstance(errors, dict):
        return bool(errors)
    if isinstance(errors, list):
        return bool(errors)
    return bool(errors)


def account_status(catalog_results):
    results = [row for row in (catalog_results or {}).values() if row]
    for row in results:
        errors = row.get("errors")
        if isinstance(errors, dict) and "access" in errors:
            return "access_error"
    if not results:
        return "missing_secret"
    if all(row.get("ok") for row in results):
        return "ok"
    return "error"


def request_body(path, key, params=None):
    req = urllib.request.Request(endpoint_url(path, params), headers={"x-apisports-key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", "replace")
            body = json.loads(raw)
            return {
                "endpoint": path,
                "params": params or {},
                "ok": 200 <= response.status < 300 and not has_api_errors(body),
                "status_code": response.status,
                "headers": safe_headers(response.headers),
                "errors": body.get("errors") if isinstance(body, dict) else None,
                "results": body.get("results") if isinstance(body, dict) else None,
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw": raw[:500]}
        return {
            "endpoint": path,
            "params": params or {},
            "ok": False,
            "status_code": exc.code,
            "headers": safe_headers(exc.headers),
            "errors": body.get("errors") if isinstance(body, dict) else str(body)[:500],
            "results": body.get("results") if isinstance(body, dict) else None,
            "body": body,
        }
    except Exception as exc:
        return {
            "endpoint": path,
            "params": params or {},
            "ok": False,
            "status_code": None,
            "headers": {},
            "errors": str(exc)[:500],
            "results": None,
            "body": {},
        }


def norm(value):
    return str(value or "").strip().lower()


def response_items(result):
    body = result.get("body") or {}
    items = body.get("response") if isinstance(body, dict) else None
    return items if isinstance(items, list) else []


def pick_bookmakers(bookmakers):
    selected = []
    for preferred in PREFERRED_BOOKMAKERS:
        for row in bookmakers:
            name = norm(row.get("name"))
            if any(excluded in name for excluded in EXCLUDED_BOOKMAKERS):
                continue
            if preferred in name and row.get("id") is not None:
                selected.append({"id": row["id"], "name": row.get("name")})
                break
    seen = set()
    out = []
    for row in selected:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        out.append(row)
    if out:
        return out[:3]
    for row in bookmakers:
        name = norm(row.get("name"))
        if any(excluded in name for excluded in EXCLUDED_BOOKMAKERS):
            continue
        if row.get("id") is None:
            continue
        out.append({"id": row["id"], "name": row.get("name")})
        if len(out) >= 3:
            break
    return out


def pick_bets(bets):
    selected = []
    for market, names in TARGET_BETS.items():
        for row in bets:
            bet_name = norm(row.get("name"))
            if any(name in bet_name for name in names) and row.get("id") is not None:
                selected.append({"market": market, "id": row["id"], "name": row.get("name")})
                break
    return selected


def candidate_dates(rows, limit=2):
    counts = Counter()
    for row in rows:
        if not row.get("bet365_verified") or row.get("event_match_method") != "exact":
            continue
        stamp = str(row.get("commence_time") or "")[:10]
        if len(stamp) == 10:
            counts[stamp] += 1
    return [date for date, _ in counts.most_common(limit)]


def load_candidates():
    try:
        rows = json.loads(CANDIDATES.read_text())
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def sample_odds(catalog_bookmakers, catalog_bets, dates, key):
    bookmakers = pick_bookmakers(catalog_bookmakers)
    bets = pick_bets(catalog_bets)
    calls = []
    for date in dates:
        for bookmaker in bookmakers[:2]:
            for bet in bets:
                if len(calls) >= MAX_ODDS_CALLS:
                    return calls, bookmakers, bets
                params = {"date": date, "bookmaker": bookmaker["id"], "bet": bet["id"]}
                result = request_body("/odds", key, params)
                calls.append(summarise_odds_call(result, bookmaker, bet, date))
    return calls, bookmakers, bets


def summarise_odds_call(result, bookmaker, bet, date):
    items = response_items(result)
    league_ids = Counter()
    fixtures = []
    observations = 0
    for item in items:
        if isinstance(item.get("league"), dict) and item["league"].get("id") is not None:
            league_ids[str(item["league"]["id"])] += 1
        fixture = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
        if fixture:
            fixtures.append({
                "fixture_id": fixture.get("id"),
                "date": fixture.get("date"),
                "timezone": fixture.get("timezone"),
            })
        bookmakers = item.get("bookmakers") if isinstance(item.get("bookmakers"), list) else []
        for book in bookmakers:
            for wager in book.get("bets") or []:
                observations += len(wager.get("values") or [])
    return {
        "date": date,
        "bookmaker": bookmaker,
        "bet": bet,
        "ok": result.get("ok"),
        "status_code": result.get("status_code"),
        "headers": result.get("headers") or {},
        "errors": result.get("errors"),
        "results": result.get("results"),
        "fixtures_returned": len(items),
        "selection_observations": observations,
        "league_ids_sample": [league_id for league_id, _ in league_ids.most_common(5)],
        "fixtures_sample": fixtures[:3],
    }


def missing_key_report(secret_name):
    return {
        "configured": bool(secret_name),
        "ok": False,
        "errors": f"Missing one of {', '.join(SECRET_NAMES)} in GitHub Secrets.",
    }


def catalog_diagnostic(result):
    if not result:
        return {}
    items = response_items(result)
    return {
        "endpoint": result.get("endpoint"),
        "ok": result.get("ok"),
        "status_code": result.get("status_code"),
        "results": result.get("results"),
        "headers": result.get("headers") or {},
        "errors": result.get("errors"),
        "items_parsed": len(items),
        "sample": items[:5],
    }


def build_report(secret_name, catalog_bookmakers, catalog_bets, odds_calls, dates, selected_bookmakers, selected_bets, catalog_results=None):
    total_fixtures = sum(int(row.get("fixtures_returned") or 0) for row in odds_calls)
    total_observations = sum(int(row.get("selection_observations") or 0) for row in odds_calls)
    catalog_results = catalog_results or {}
    status = account_status(catalog_results) if secret_name else "missing_secret"
    return {
        "generated_at": now_iso(),
        "mode": "SHADOW_ONLY",
        "production_impact": "none",
        "provider": "API-Football / API-Sports",
        "configured_secret": secret_name,
        "configured": bool(secret_name),
        "account_status": status,
        "sample_version": SAMPLE_VERSION,
        "max_odds_calls": MAX_ODDS_CALLS,
        "target_dates": dates,
        "selected_bookmakers": selected_bookmakers,
        "selected_bets": selected_bets,
        "catalogs": {
            "bookmakers_ok": bool(catalog_bookmakers),
            "bookmakers_count": len(catalog_bookmakers),
            "bets_ok": bool(catalog_bets),
            "bets_count": len(catalog_bets),
            "diagnostics": {
                "bookmakers": catalog_diagnostic(catalog_results.get("bookmakers")),
                "bets": catalog_diagnostic(catalog_results.get("bets")),
            },
        },
        "coverage": {
            "odds_calls": len(odds_calls),
            "successful_odds_calls": sum(1 for row in odds_calls if row.get("ok")),
            "fixtures_returned": total_fixtures,
            "selection_observations": total_observations,
            "has_external_market_sample": total_observations > 0,
            "blocked_by_account_status": status != "ok",
        },
        "promotion_blockers": [
            "No production use until fixture matching to Bet365 candidates is exact or defensibly conservative.",
            "No production use until odds freshness/update timestamps are understood.",
            "No production use until bookmaker economic_source_id is mapped per bookmaker.",
        ],
        "provenance_template": {
            "transport_provider_id": "api-sports:api-football",
            "economic_source_id": "api-football:bookmaker:<bookmaker_id>",
            "evidence_family": "external_market_price",
            "model_or_feed_version": SAMPLE_VERSION,
        },
        "odds_calls": odds_calls,
    }


def markdown(report):
    lines = [
        "# API-Football odds sample",
        "",
        f"Generated: {report['generated_at']}",
        f"Mode: {report['mode']}",
        f"Production impact: {report['production_impact']}",
        f"Configured: {report['configured']}",
        "",
        "## Coverage",
        f"- Odds calls: {report['coverage']['odds_calls']}",
        f"- Successful odds calls: {report['coverage']['successful_odds_calls']}",
        f"- Fixtures returned: {report['coverage']['fixtures_returned']}",
        f"- Selection observations: {report['coverage']['selection_observations']}",
        "",
        "## Catalog diagnostics",
        f"- Bookmakers parsed: {report['catalogs']['bookmakers_count']}",
        f"- Bets parsed: {report['catalogs']['bets_count']}",
        "",
        "## Selected bookmakers",
    ]
    lines.extend(f"- {row.get('id')}: {row.get('name')}" for row in report["selected_bookmakers"])
    lines.append("")
    lines.append("## Selected bets")
    lines.extend(f"- {row.get('market')}: {row.get('id')} {row.get('name')}" for row in report["selected_bets"])
    lines.append("")
    lines.append("## Promotion blockers")
    lines.extend(f"- {item}" for item in report["promotion_blockers"])
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    secret_name, key = api_key()
    if not key:
        report = build_report(secret_name, [], [], [], [], [], [])
        report["coverage"]["error"] = missing_key_report(secret_name)["errors"]
    else:
        bookmakers_result = request_body("/odds/bookmakers", key)
        bets_result = request_body("/odds/bets", key)
        bookmakers = response_items(bookmakers_result)
        bets = response_items(bets_result)
        dates = candidate_dates(load_candidates())
        odds_calls, selected_bookmakers, selected_bets = sample_odds(bookmakers, bets, dates, key)
        report = build_report(
            secret_name,
            bookmakers,
            bets,
            odds_calls,
            dates,
            selected_bookmakers,
            selected_bets,
            {"bookmakers": bookmakers_result, "bets": bets_result},
        )

    OUT.mkdir(exist_ok=True)
    STATUS_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    STATUS_MD.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({
        "configured": report["configured"],
        "odds_calls": report["coverage"]["odds_calls"],
        "fixtures_returned": report["coverage"]["fixtures_returned"],
        "selection_observations": report["coverage"]["selection_observations"],
        "production_impact": report["production_impact"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
