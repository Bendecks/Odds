import json
import pathlib
from collections import Counter, defaultdict
from datetime import datetime, timezone


CANDIDATES = pathlib.Path("data/value_candidates.json")
REFERENCE_QUALITY = pathlib.Path("output/reference_quality_shadow.json")
OUT = pathlib.Path("output/football_model_readiness.json")

MODEL_VERSION = "football-model-readiness-v1"
MODEL_COVERABLE_MARKETS = {"h2h", "totals", "btts"}
FIRST_MODEL_MARKETS = {"h2h", "totals"}
PUBLIC_DATA_HINTS = {
    "premier league": "football-data.co.uk:E0",
    "championship": "football-data.co.uk:E1",
    "bundesliga": "football-data.co.uk:D1",
    "la liga": "football-data.co.uk:SP1",
    "serie a": "football-data.co.uk:I1",
    "ligue 1": "football-data.co.uk:F1",
    "eredivisie": "football-data.co.uk:N1",
    "champions league": "football-data.co.uk:CL",
    "superliga": "public-data:needs-provider-specific-mapping",
}


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def norm(value):
    return str(value or "").strip().lower()


def has_value(row, field):
    return bool(str(row.get(field) or "").strip())


def split_event_name(event):
    text = str(event or "")
    for marker in (" vs ", " v ", " - "):
        if marker in text:
            left, right = text.split(marker, 1)
            left, right = left.strip(), right.strip()
            if left and right:
                return left, right
    return None, None


def public_data_hint(league):
    league_norm = norm(league)
    for needle, source in PUBLIC_DATA_HINTS.items():
        if needle in league_norm:
            return source
    return None


def fresh_exact_market_counts(rqg):
    rows = ((rqg.get("unlock_priorities") or {}).get("market_priorities") or [])
    return {
        str(row.get("market") or "unknown"): int(row.get("fresh_exact_candidates") or 0)
        for row in rows
    }


def build_report(candidates, rqg):
    if not isinstance(candidates, list):
        candidates = []
    market_counts = Counter(str(row.get("market") or "unknown") for row in candidates)
    exact = [
        row
        for row in candidates
        if row.get("bet365_verified") and row.get("event_match_method") == "exact"
    ]
    fresh_by_market = fresh_exact_market_counts(rqg if isinstance(rqg, dict) else {})
    rows_with_sport = sum(1 for row in candidates if has_value(row, "sport"))
    rows_with_league = sum(1 for row in candidates if has_value(row, "league"))
    rows_with_teams = 0
    league_counts = Counter()
    public_hints = Counter()
    coverable_by_market = Counter()
    missing_by_market = defaultdict(Counter)

    for row in candidates:
        home, away = split_event_name(row.get("event"))
        if home and away:
            rows_with_teams += 1
        league = row.get("league")
        if has_value(row, "league"):
            league_counts[str(league)] += 1
            hint = public_data_hint(league)
            if hint:
                public_hints[hint] += 1
        market = str(row.get("market") or "unknown")
        if market in MODEL_COVERABLE_MARKETS and home and away and has_value(row, "league"):
            coverable_by_market[market] += 1
        else:
            if market not in MODEL_COVERABLE_MARKETS:
                missing_by_market[market]["market_not_first_model_scope"] += 1
            if not (home and away):
                missing_by_market[market]["team_parse_missing"] += 1
            if not has_value(row, "league"):
                missing_by_market[market]["league_missing"] += 1
            if not has_value(row, "sport"):
                missing_by_market[market]["sport_missing"] += 1

    first_scope = sum(
        count for market, count in coverable_by_market.items() if market in FIRST_MODEL_MARKETS
    )
    blockers = []
    if rows_with_league < len(candidates):
        blockers.append("candidate_league_metadata_missing_until_next_feed")
    if not public_hints:
        blockers.append("public_data_league_mapping_not_verified")
    blockers.append("historical_results_adapter_not_yet_built")
    blockers.append("model_reference_must_remain_shadow_until_calibrated")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "SHADOW_ONLY",
        "production_impact": "none",
        "model_version": MODEL_VERSION,
        "purpose": "Measure whether current football candidates have enough event, league and market metadata for a future Bet365-independent Dixon-Coles/Elo model reference.",
        "reference_quality_role_if_promoted": "model_reference",
        "candidate_rows": len(candidates),
        "exact_bet365_rows": len(exact),
        "fresh_exact_rows_by_market": dict(sorted(fresh_by_market.items())),
        "metadata": {
            "rows_with_sport": rows_with_sport,
            "rows_with_league": rows_with_league,
            "rows_with_parseable_teams": rows_with_teams,
            "sport_coverage": round(rows_with_sport / len(candidates), 4) if candidates else 0,
            "league_coverage": round(rows_with_league / len(candidates), 4) if candidates else 0,
            "team_parse_coverage": round(rows_with_teams / len(candidates), 4) if candidates else 0,
        },
        "market_scope": {
            "candidate_markets": dict(sorted(market_counts.items())),
            "first_model_markets": sorted(FIRST_MODEL_MARKETS),
            "coverable_rows_by_market": dict(sorted(coverable_by_market.items())),
            "first_model_scope_rows": first_scope,
        },
        "league_mapping": {
            "top_candidate_leagues": league_counts.most_common(10),
            "public_data_hints": dict(sorted(public_hints.items())),
        },
        "blockers": blockers,
        "missing_by_market": {
            market: dict(sorted(counter.items()))
            for market, counter in sorted(missing_by_market.items())
        },
        "next_action": "Build a SHADOW_ONLY historical-results adapter for mapped leagues, then calibrate Dixon-Coles/Elo probabilities before allowing the model_reference role.",
    }


def main():
    report = build_report(load_json(CANDIDATES, []), load_json(REFERENCE_QUALITY, {}))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "candidate_rows": report["candidate_rows"],
        "league_coverage": report["metadata"]["league_coverage"],
        "first_model_scope_rows": report["market_scope"]["first_model_scope_rows"],
        "production_impact": report["production_impact"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
