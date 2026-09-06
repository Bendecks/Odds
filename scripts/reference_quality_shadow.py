import json
import pathlib
from collections import Counter, defaultdict
from datetime import datetime, timezone

import operational_status as ops


CANDIDATES = pathlib.Path("data/value_candidates.json")
STATUS = pathlib.Path("output/operational_status.json")
OUT = pathlib.Path("output/reference_quality_shadow.json")

TARGET_GATE_VERSION = "reference-quality-shadow-v1"
REQUIRED_ROLES = ("unibet_reference", "external_market_reference", "model_reference")
PROVENANCE_FIELDS = (
    "transport_provider_id",
    "economic_source_id",
    "evidence_family",
    "model_or_feed_version",
)
BET365_IDS = {"bet365", "bookmaker:bet365", "odds-api.io:bet365"}


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def norm(value):
    return str(value or "").strip().lower()


def analysis_time():
    status = load_json(STATUS, {})
    stamp = ops.parse_dt(status.get("generated_at"))
    return stamp or datetime.now(timezone.utc)


def has_complete_provenance(source):
    return all(str(source.get(field) or "").strip() for field in PROVENANCE_FIELDS)


def is_bet365(source):
    economic_source = norm(source.get("economic_source_id"))
    return economic_source in BET365_IDS or "bet365" in economic_source


def source_role(source):
    economic_source = norm(source.get("economic_source_id"))
    family = norm(source.get("evidence_family"))
    if economic_source == "unibet":
        return "unibet_reference"
    if "model" in family or economic_source.startswith("model:"):
        return "model_reference"
    if "market" in family or "price" in family or "bookmaker" in family:
        return "external_market_reference"
    return "unknown_reference"


def fresh_exact_candidate(candidate, now):
    return ops.exact_identity(candidate) and ops.fresh_bet365(candidate, now)


def evaluate_candidate(candidate, now):
    sources = candidate.get("reference_sources")
    if not isinstance(sources, list):
        sources = []

    complete_sources = [s for s in sources if isinstance(s, dict) and has_complete_provenance(s)]
    missing_provenance = len(complete_sources) != len(sources)
    independent_sources = {
        norm(s.get("economic_source_id"))
        for s in complete_sources
        if norm(s.get("economic_source_id")) and not is_bet365(s)
    }
    role_sources = defaultdict(set)
    ignored_sources = []

    for source in complete_sources:
        economic_source = norm(source.get("economic_source_id"))
        if not economic_source:
            missing_provenance = True
            continue
        if is_bet365(source):
            ignored_sources.append(economic_source)
            continue
        role_sources[source_role(source)].add(economic_source)

    roles_present = sorted(role for role in REQUIRED_ROLES if role_sources.get(role))
    missing_roles = [role for role in REQUIRED_ROLES if not role_sources.get(role)]
    reasons = []
    if not fresh_exact_candidate(candidate, now):
        reasons.append("not_fresh_exact_bet365")
    if missing_provenance:
        reasons.append("missing_reference_provenance")
    for role in missing_roles:
        reasons.append(f"missing_{role}")
    if len(independent_sources) < len(REQUIRED_ROLES):
        reasons.append("insufficient_independent_economic_sources")

    return {
        "event": candidate.get("event"),
        "event_id": candidate.get("event_id"),
        "bet365_event_id": candidate.get("bet365_event_id"),
        "market": candidate.get("market") or "unknown",
        "pick": candidate.get("pick"),
        "line": candidate.get("line"),
        "fresh_exact_bet365": fresh_exact_candidate(candidate, now),
        "shadow_ready": not reasons,
        "roles_present": roles_present,
        "missing_roles": missing_roles,
        "independent_economic_sources": sorted(independent_sources),
        "ignored_economic_sources": sorted(set(ignored_sources)),
        "failure_reasons": reasons,
    }


def summarise(evaluations):
    by_market = defaultdict(lambda: {
        "evaluated": 0,
        "fresh_exact_bet365": 0,
        "shadow_ready": 0,
        "failure_reasons": Counter(),
        "missing_roles": Counter(),
    })
    reasons = Counter()
    missing_roles = Counter()
    for row in evaluations:
        market = str(row.get("market") or "unknown")
        bucket = by_market[market]
        bucket["evaluated"] += 1
        if row["fresh_exact_bet365"]:
            bucket["fresh_exact_bet365"] += 1
        if row["shadow_ready"]:
            bucket["shadow_ready"] += 1
        for reason in row["failure_reasons"]:
            bucket["failure_reasons"][reason] += 1
            reasons[reason] += 1
        for role in row["missing_roles"]:
            bucket["missing_roles"][role] += 1
            missing_roles[role] += 1

    return {
        "failure_reasons": dict(sorted(reasons.items())),
        "missing_roles": dict(sorted(missing_roles.items())),
        "by_market": {
            market: {
                "evaluated": data["evaluated"],
                "fresh_exact_bet365": data["fresh_exact_bet365"],
                "shadow_ready": data["shadow_ready"],
                "failure_reasons": dict(sorted(data["failure_reasons"].items())),
                "missing_roles": dict(sorted(data["missing_roles"].items())),
            }
            for market, data in sorted(by_market.items())
        },
    }


def unlock_priorities(fresh_exact):
    role_gap = Counter()
    paired_role_gap = Counter()
    market_gap = defaultdict(lambda: {"fresh_exact": 0, "shadow_ready": 0, "missing_roles": Counter()})

    for row in fresh_exact:
        market = str(row.get("market") or "unknown")
        market_gap[market]["fresh_exact"] += 1
        if row["shadow_ready"]:
            market_gap[market]["shadow_ready"] += 1
        missing = tuple(sorted(row["missing_roles"]))
        if missing:
            paired_role_gap[" + ".join(missing)] += 1
        for role in missing:
            role_gap[role] += 1
            market_gap[market]["missing_roles"][role] += 1

    markets = []
    for market, data in market_gap.items():
        missing_roles = dict(sorted(data["missing_roles"].items()))
        markets.append({
            "market": market,
            "fresh_exact_candidates": data["fresh_exact"],
            "shadow_ready_candidates": data["shadow_ready"],
            "missing_roles": missing_roles,
            "largest_missing_role": max(missing_roles, key=missing_roles.get) if missing_roles else None,
        })
    markets.sort(key=lambda row: (-row["fresh_exact_candidates"], row["market"]))

    role_actions = []
    for role, count in sorted(role_gap.items(), key=lambda item: (-item[1], item[0])):
        alone_unlocks = sum(1 for row in fresh_exact if row["missing_roles"] == [role])
        role_actions.append({
            "role": role,
            "fresh_exact_candidates_blocked": count,
            "would_unlock_if_added_alone": alone_unlocks,
        })

    paired = [
        {"missing_role_set": role_set, "fresh_exact_candidates_blocked": count}
        for role_set, count in sorted(paired_role_gap.items(), key=lambda item: (-item[1], item[0]))
    ]
    first_market = markets[0]["market"] if markets else None
    first_market_rows = markets[0]["fresh_exact_candidates"] if markets else 0
    return {
        "role_gap_priorities": role_actions,
        "paired_role_gaps": paired,
        "market_priorities": markets,
        "recommended_next_unlock": {
            "summary": "Add both an external market reference and a model reference before expecting shadow-ready candidates."
            if paired else "No current Reference Quality role gap among fresh exact candidates.",
            "first_market_focus": first_market,
            "first_market_fresh_exact_candidates": first_market_rows,
            "single_role_unlock_possible": any(row["would_unlock_if_added_alone"] > 0 for row in role_actions),
            "production_impact": "none",
        },
    }


def build_report(candidates, now=None):
    now = now or analysis_time()
    evaluations = [evaluate_candidate(candidate, now) for candidate in candidates]
    fresh_exact = [row for row in evaluations if row["fresh_exact_bet365"]]
    shadow_ready = [row for row in evaluations if row["shadow_ready"]]
    summary = summarise(fresh_exact)
    all_summary = summarise(evaluations)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": now.isoformat(),
        "mode": "SHADOW_ONLY",
        "production_impact": "none",
        "target_gate_version": TARGET_GATE_VERSION,
        "purpose": "Evaluate whether fresh exact Bet365 candidates have the independent evidence roles needed for a future replacement Reference Quality Gate.",
        "requirements": {
            "required_roles": list(REQUIRED_ROLES),
            "min_independent_economic_sources": len(REQUIRED_ROLES),
            "excluded_execution_source": "bet365",
            "required_provenance_fields": list(PROVENANCE_FIELDS),
        },
        "total_candidates": len(candidates),
        "fresh_exact_candidates": len(fresh_exact),
        "shadow_ready_candidates": len(shadow_ready),
        "failure_reasons": summary["failure_reasons"],
        "missing_roles": summary["missing_roles"],
        "by_market": summary["by_market"],
        "unlock_priorities": unlock_priorities(fresh_exact),
        "all_candidates_by_market": all_summary["by_market"],
        "sample_failures": [row for row in evaluations if not row["shadow_ready"]][:10],
        "sample_shadow_ready": shadow_ready[:10],
    }


def main():
    candidates = load_json(CANDIDATES, [])
    if not isinstance(candidates, list):
        candidates = []
    report = build_report(candidates)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "mode": report["mode"],
        "production_impact": report["production_impact"],
        "fresh_exact_candidates": report["fresh_exact_candidates"],
        "shadow_ready_candidates": report["shadow_ready_candidates"],
        "missing_roles": report["missing_roles"],
        "recommended_next_unlock": report["unlock_priorities"]["recommended_next_unlock"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
