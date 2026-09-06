import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


OUT = pathlib.Path("output")
STATUS_JSON = OUT / "api_football_poc_status.json"
STATUS_MD = OUT / "api_football_poc_status.md"
BASE_URL = "https://v3.football.api-sports.io"
SECRET_NAMES = ("API_FOOTBALL_KEY", "APISPORTS_KEY")
PROBE_VERSION = "api-football-poc-v1"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def api_key():
    for name in SECRET_NAMES:
        value = os.getenv(name, "").strip()
        if value:
            return name, value
    return None, ""


def safe_headers(headers):
    wanted = (
        "x-ratelimit-requests-limit",
        "x-ratelimit-requests-remaining",
        "x-ratelimit-requests-reset",
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
        "retry-after",
    )
    lower = {str(k).lower(): str(v) for k, v in dict(headers).items()}
    return {key: lower[key] for key in wanted if key in lower}


def endpoint_url(path, params=None):
    query = urllib.parse.urlencode(params or {})
    return f"{BASE_URL}{path}" + (f"?{query}" if query else "")


def request_json(path, key, params=None):
    url = endpoint_url(path, params)
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", "replace")
            try:
                body = json.loads(raw)
            except Exception:
                body = {"raw": raw[:500]}
            return {
                "endpoint": path,
                "configured": True,
                "ok": 200 <= response.status < 300,
                "status_code": response.status,
                "headers": safe_headers(response.headers),
                "errors": body.get("errors") if isinstance(body, dict) else None,
                "results": body.get("results") if isinstance(body, dict) else None,
                "sample": sample_response(body),
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw": raw[:500]}
        return {
            "endpoint": path,
            "configured": True,
            "ok": False,
            "status_code": exc.code,
            "headers": safe_headers(exc.headers),
            "errors": body.get("errors") if isinstance(body, dict) else str(body)[:500],
            "results": body.get("results") if isinstance(body, dict) else None,
            "sample": sample_response(body),
        }
    except Exception as exc:
        return {
            "endpoint": path,
            "configured": True,
            "ok": False,
            "status_code": None,
            "headers": {},
            "errors": str(exc)[:500],
            "results": None,
            "sample": None,
        }


def sample_response(body):
    if isinstance(body, dict):
        response = body.get("response")
        if isinstance(response, list):
            return response[:3]
        return {key: body.get(key) for key in ("get", "parameters", "paging") if key in body}
    if isinstance(body, list):
        return body[:3]
    return str(body)[:500]


def missing_key_report():
    return {
        "endpoint": None,
        "configured": False,
        "ok": False,
        "status_code": None,
        "headers": {},
        "errors": f"Missing one of {', '.join(SECRET_NAMES)} in GitHub Secrets.",
        "results": None,
        "sample": None,
    }


def provenance_contract():
    return {
        "transport_provider_id": "api-sports:api-football",
        "economic_source_id": "api-football:bookmaker:<bookmaker_id>",
        "evidence_family": "external_market_price",
        "model_or_feed_version": PROBE_VERSION,
    }


def build_report(entries, secret_name):
    configured = bool(secret_name)
    ok_entries = [row for row in entries if row.get("ok")]
    bookmaker_probe = next((row for row in entries if row.get("endpoint") == "/odds/bookmakers"), {})
    bet_probe = next((row for row in entries if row.get("endpoint") == "/odds/bets"), {})
    return {
        "generated_at": now_iso(),
        "mode": "SHADOW_ONLY",
        "production_impact": "none",
        "provider": "API-Football / API-Sports",
        "base_url": BASE_URL,
        "credential_secret_names": list(SECRET_NAMES),
        "configured_secret": secret_name,
        "configured": configured,
        "ok": configured and len(ok_entries) == len(entries),
        "purpose": "Probe API-Football as a potential independent external market reference without affecting PAPER PICK qualification.",
        "required_before_reference_role": [
            "API key configured",
            "bookmaker ids observable",
            "target markets observable",
            "fresh pre-match odds for same events as Bet365 candidates",
            "economic_source_id mapped per bookmaker",
        ],
        "provenance_contract": provenance_contract(),
        "reference_quality_role_if_promoted": "external_market_reference",
        "active_provider_policy": "Odds-API.io remains the active Bet365/Unibet provider; API-Football is SHADOW_ONLY until explicitly promoted as independent evidence.",
        "bookmaker_catalog_observable": bool(bookmaker_probe.get("ok") and (bookmaker_probe.get("results") or bookmaker_probe.get("sample"))),
        "bet_catalog_observable": bool(bet_probe.get("ok") and (bet_probe.get("results") or bet_probe.get("sample"))),
        "endpoints": entries,
    }


def markdown(report):
    lines = [
        "# API-Football external reference PoC",
        "",
        f"Generated: {report['generated_at']}",
        f"Mode: {report['mode']}",
        f"Production impact: {report['production_impact']}",
        f"Configured: {report['configured']}",
        f"OK: {report['ok']}",
        "",
        "This probe is only for evaluating API-Football/API-Sports as a future independent external market reference.",
        "It must not change PAPER PICK qualification until freshness, coverage and provenance are validated.",
        "",
        "## Provenance contract",
        "```json",
        json.dumps(report["provenance_contract"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Required before promotion",
    ]
    lines.extend(f"- {item}" for item in report["required_before_reference_role"])
    lines.append("")
    lines.append("## Endpoint probes")
    for row in report["endpoints"]:
        lines.extend([
            "",
            f"### {row.get('endpoint') or 'credentials'}",
            f"- configured: {row.get('configured')}",
            f"- ok: {row.get('ok')}",
            f"- status_code: {row.get('status_code')}",
            f"- results: {row.get('results')}",
        ])
        if row.get("errors"):
            lines.extend(["- errors:", "```json", json.dumps(row.get("errors"), ensure_ascii=False, indent=2), "```"])
        if row.get("headers"):
            lines.extend(["- headers:", "```json", json.dumps(row.get("headers"), ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines) + "\n"


def main():
    secret_name, key = api_key()
    if key:
        entries = [
            request_json("/status", key),
            request_json("/odds/bookmakers", key),
            request_json("/odds/bets", key),
        ]
    else:
        entries = [missing_key_report()]
    report = build_report(entries, secret_name)
    OUT.mkdir(exist_ok=True)
    STATUS_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    STATUS_MD.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({
        "provider": report["provider"],
        "configured": report["configured"],
        "ok": report["ok"],
        "mode": report["mode"],
        "production_impact": report["production_impact"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
