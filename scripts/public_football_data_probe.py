import csv
import io
import json
import pathlib
import urllib.error
import urllib.request
from datetime import datetime, timezone


OUT = pathlib.Path("output")
STATUS_JSON = OUT / "public_football_data_probe.json"
STATUS_MD = OUT / "public_football_data_probe.md"
FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk/mmz4281"
OPENFOOTBALL_BASE_URL = "https://raw.githubusercontent.com/openfootball/football.json/master"
PROBE_VERSION = "public-football-data-probe-v1"
DEFAULT_TIMEOUT = 20
FOOTBALL_DATA_TIMEOUT = 5
OPENFOOTBALL_TIMEOUT = 20
MAX_SAMPLE_ROWS = 5

LEAGUES = [
    {"code": "E0", "openfootball": "en.1", "country": "England", "league": "Premier League"},
    {"code": "E1", "openfootball": "en.2", "country": "England", "league": "Championship"},
    {"code": "D1", "openfootball": "de.1", "country": "Germany", "league": "Bundesliga"},
    {"code": "SP1", "openfootball": "es.1", "country": "Spain", "league": "La Liga"},
    {"code": "I1", "openfootball": "it.1", "country": "Italy", "league": "Serie A"},
    {"code": "F1", "openfootball": "fr.1", "country": "France", "league": "Ligue 1"},
    {"code": "N1", "openfootball": "nl.1", "country": "Netherlands", "league": "Eredivisie"},
]

REQUIRED_COLUMNS = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def season_code(today=None):
    today = today or datetime.now(timezone.utc).date()
    start_year = today.year if today.month >= 7 else today.year - 1
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def season_slug(today=None):
    today = today or datetime.now(timezone.utc).date()
    start_year = today.year if today.month >= 7 else today.year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def csv_url(season, league_code):
    return f"{FOOTBALL_DATA_BASE_URL}/{season}/{league_code}.csv"


def openfootball_url(season, league_code):
    return f"{OPENFOOTBALL_BASE_URL}/{season}/{league_code}.json"


def fetch_text(url, timeout=DEFAULT_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "Odds-Lab-public-football-data-probe/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return {
            "ok": 200 <= response.status < 300,
            "status_code": response.status,
            "content_type": response.headers.get("content-type"),
            "text": raw.decode("utf-8-sig", "replace"),
        }


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    columns = set(reader.fieldnames or [])
    rows = []
    completed_rows = 0
    parseable_rows = 0
    for row in reader:
        if not any(row.values()):
            continue
        rows.append(row)
        if row.get("HomeTeam") and row.get("AwayTeam") and row.get("Date"):
            parseable_rows += 1
        if row.get("FTHG") not in (None, "") and row.get("FTAG") not in (None, ""):
            completed_rows += 1
    missing = sorted(REQUIRED_COLUMNS - columns)
    return {
        "columns": sorted(columns),
        "missing_required_columns": missing,
        "row_count": len(rows),
        "parseable_rows": parseable_rows,
        "completed_result_rows": completed_rows,
        "sample": [
            {
                "date": row.get("Date"),
                "home": row.get("HomeTeam"),
                "away": row.get("AwayTeam"),
                "home_goals": row.get("FTHG"),
                "away_goals": row.get("FTAG"),
                "result": row.get("FTR"),
            }
            for row in rows[:MAX_SAMPLE_ROWS]
        ],
    }


def parse_openfootball_json(text):
    body = json.loads(text)
    matches = body.get("matches") if isinstance(body, dict) else None
    if not isinstance(matches, list):
        matches = []
    parseable_rows = 0
    completed_rows = 0
    sample = []
    for row in matches:
        if not isinstance(row, dict):
            continue
        if row.get("date") and row.get("team1") and row.get("team2"):
            parseable_rows += 1
        score = row.get("score")
        ft = score.get("ft") if isinstance(score, dict) else score
        if isinstance(ft, list) and len(ft) >= 2 and ft[0] is not None and ft[1] is not None:
            completed_rows += 1
        if len(sample) < MAX_SAMPLE_ROWS:
            sample.append({
                "date": row.get("date"),
                "home": row.get("team1"),
                "away": row.get("team2"),
                "home_goals": ft[0] if isinstance(ft, list) and len(ft) >= 1 else None,
                "away_goals": ft[1] if isinstance(ft, list) and len(ft) >= 2 else None,
                "result": None,
            })
    return {
        "competition_name": body.get("name") if isinstance(body, dict) else None,
        "missing_required_columns": [],
        "row_count": len(matches),
        "parseable_rows": parseable_rows,
        "completed_result_rows": completed_rows,
        "sample": sample,
    }


def error_result(source, season, league, url, error, status_code=None, content_type=None):
    return {
        **league,
        "source": source,
        "season": season,
        "url": url,
        "ok": False,
        "status_code": status_code,
        "content_type": content_type,
        "error": error,
        "missing_required_columns": sorted(REQUIRED_COLUMNS),
        "row_count": 0,
        "parseable_rows": 0,
        "completed_result_rows": 0,
        "sample": [],
    }


def probe_csv_league(season, league):
    url = csv_url(season, league["code"])
    try:
        fetched = fetch_text(url, timeout=FOOTBALL_DATA_TIMEOUT)
        parsed = parse_csv(fetched["text"])
        data_ready = bool(fetched["ok"] and not parsed["missing_required_columns"] and parsed["parseable_rows"])
        return {
            **league,
            "source": "football-data.co.uk",
            "season": season,
            "url": url,
            "ok": data_ready,
            "status_code": fetched["status_code"],
            "content_type": fetched["content_type"],
            "error": None,
            **parsed,
        }
    except urllib.error.HTTPError as exc:
        content_type = dict(exc.headers).get("content-type") if exc.headers else None
        return error_result("football-data.co.uk", season, league, url, f"HTTPError: {exc.code}", exc.code, content_type)
    except Exception as exc:
        return error_result("football-data.co.uk", season, league, url, str(exc)[:500])


def probe_openfootball_league(season, league):
    code = league.get("openfootball")
    url = openfootball_url(season, code)
    try:
        fetched = fetch_text(url, timeout=OPENFOOTBALL_TIMEOUT)
        parsed = parse_openfootball_json(fetched["text"])
        data_ready = bool(fetched["ok"] and parsed["parseable_rows"])
        return {
            **league,
            "source": "openfootball/football.json",
            "season": season,
            "url": url,
            "ok": data_ready,
            "status_code": fetched["status_code"],
            "content_type": fetched["content_type"],
            "error": None,
            **parsed,
        }
    except urllib.error.HTTPError as exc:
        content_type = dict(exc.headers).get("content-type") if exc.headers else None
        return error_result("openfootball/football.json", season, league, url, f"HTTPError: {exc.code}", exc.code, content_type)
    except Exception as exc:
        return error_result("openfootball/football.json", season, league, url, str(exc)[:500])


def source_summary(results):
    summary = {}
    for row in results:
        source = row.get("source") or "unknown"
        info = summary.setdefault(source, {"attempted": 0, "data_ready": 0, "rows": 0, "completed_result_rows": 0})
        info["attempted"] += 1
        if row.get("ok"):
            info["data_ready"] += 1
        info["rows"] += int(row.get("row_count") or 0)
        info["completed_result_rows"] += int(row.get("completed_result_rows") or 0)
    for info in summary.values():
        info["source_status"] = "ok" if info["data_ready"] else "source_unavailable"
    return dict(sorted(summary.items()))


def build_report(results, season, openfootball_season=None):
    valid = [row for row in results if row.get("ok")]
    attempted = len(results)
    source_status = "ok" if valid else "source_unavailable"
    sources = source_summary(results)
    return {
        "generated_at": now_iso(),
        "mode": "SHADOW_ONLY",
        "production_impact": "none",
        "probe_version": PROBE_VERSION,
        "provider": "public football results data",
        "base_url": FOOTBALL_DATA_BASE_URL,
        "season": season,
        "openfootball_season": openfootball_season,
        "purpose": "Probe free public football results data for a future Bet365-independent Dixon-Coles/Elo model reference.",
        "reference_quality_role_if_promoted": "model_reference",
        "active_provider_policy": "Odds-API.io remains the only active odds provider; this is public historical results data and cannot create PAPER PICKS directly.",
        "source_status": source_status,
        "sources": sources,
        "leagues_attempted": attempted,
        "leagues_data_ready": len(valid),
        "has_any_valid_league": bool(valid),
        "required_before_model_role": [
            "stable public results coverage for target leagues",
            "candidate league names mapped to public data league codes",
            "historical-results adapter implemented",
            "Dixon-Coles/Elo probabilities calibrated out-of-sample",
            "model role shadow-tested inside Reference Quality Gate",
        ],
        "leagues": results,
    }


def markdown(report):
    lines = [
        "# Public football data probe",
        "",
        f"Generated: {report['generated_at']}",
        f"Mode: {report['mode']}",
        f"Production impact: {report['production_impact']}",
        f"Provider: {report['provider']}",
        f"Football-Data season: {report['season']}",
        f"Openfootball season: {report.get('openfootball_season') or '-'}",
        f"Source status: {report['source_status']}",
        f"Leagues data-ready: {report['leagues_data_ready']} / {report['leagues_attempted']}",
        "",
        "This probe validates public match-result CSV availability for future SHADOW_ONLY model work.",
        "It does not affect PAPER PICK qualification and does not count as calibrated model evidence.",
        "",
        "## Required before model-role promotion",
    ]
    lines.extend(f"- {item}" for item in report["required_before_model_role"])
    lines.extend(["", "## Source summary"])
    for source, row in report.get("sources", {}).items():
        lines.extend([
            "",
            f"### {source}",
            f"- status: {row.get('source_status')}",
            f"- data_ready: {row.get('data_ready')} / {row.get('attempted')}",
            f"- rows: {row.get('rows')}",
            f"- completed_result_rows: {row.get('completed_result_rows')}",
        ])
    lines.extend(["", "## League probes"])
    for row in report["leagues"]:
        lines.extend([
            "",
            f"### {row['league']} ({row.get('source')}, {row['code']})",
            f"- ok: {row['ok']}",
            f"- status_code: {row.get('status_code')}",
            f"- row_count: {row.get('row_count')}",
            f"- completed_result_rows: {row.get('completed_result_rows')}",
            f"- url: {row.get('url')}",
        ])
        if row.get("error"):
            lines.append(f"- error: {row['error']}")
        if row.get("missing_required_columns"):
            lines.append(f"- missing_required_columns: {', '.join(row['missing_required_columns'])}")
    return "\n".join(lines) + "\n"


def main():
    csv_season = season_code()
    json_season = season_slug()
    results = [probe_csv_league(csv_season, league) for league in LEAGUES]
    results.extend(probe_openfootball_league(json_season, league) for league in LEAGUES)
    report = build_report(results, csv_season, json_season)
    OUT.mkdir(exist_ok=True)
    STATUS_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    STATUS_MD.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({
        "provider": report["provider"],
        "season": report["season"],
        "openfootball_season": report["openfootball_season"],
        "source_status": report["source_status"],
        "leagues_data_ready": report["leagues_data_ready"],
        "production_impact": report["production_impact"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
