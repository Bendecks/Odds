import json
import pathlib
from datetime import datetime, timezone


OPERATIONAL = pathlib.Path("output/operational_status.json")
REFERENCE_QUALITY = pathlib.Path("output/reference_quality_shadow.json")
OUT = pathlib.Path("output/paper_pick_readiness.json")


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def pct(part, total):
    return round(part / total, 4) if total else 0.0


def market_rows(rqg):
    priorities = ((rqg.get("unlock_priorities") or {}).get("market_priorities") or [])
    return [
        {
            "market": row.get("market") or "unknown",
            "fresh_exact_candidates": int(row.get("fresh_exact_candidates") or 0),
            "shadow_ready_candidates": int(row.get("shadow_ready_candidates") or 0),
            "missing_roles": row.get("missing_roles") or {},
        }
        for row in priorities
    ]


def build_report(operational, rqg):
    funnel = operational.get("funnel") or {}
    candidate_rows = int(funnel.get("candidate_rows") or 0)
    fair_rows = int(funnel.get("fair_probability_rows") or 0)
    exact_rows = int(funnel.get("exact_bet365_rows") or 0)
    fresh_rows = int(funnel.get("fresh_exact_bet365_rows") or 0)
    legacy_depth_rows = int(funnel.get("reference_depth_ready_rows") or 0)
    qualified_rows = int(funnel.get("qualified_now_rows") or 0)

    missing_roles = rqg.get("missing_roles") or {}
    shadow_ready = int(rqg.get("shadow_ready_candidates") or 0)
    fresh_exact_shadow = int(rqg.get("fresh_exact_candidates") or fresh_rows)
    markets = market_rows(rqg)
    first_market = markets[0] if markets else {}
    blockers = [
        {"blocker": "external_market_reference", "fresh_exact_candidates_blocked": int(missing_roles.get("external_market_reference") or 0)},
        {"blocker": "model_reference", "fresh_exact_candidates_blocked": int(missing_roles.get("model_reference") or 0)},
        {"blocker": "legacy_min_reference_books", "fresh_exact_candidates_blocked": max(0, fresh_rows - legacy_depth_rows)},
    ]
    blockers = [row for row in blockers if row["fresh_exact_candidates_blocked"] > 0]
    blockers.sort(key=lambda row: (-row["fresh_exact_candidates_blocked"], row["blocker"]))

    if qualified_rows:
        stage = "paper_picks_available"
        summary = "Der er allerede kvalificerede PAPER PICKS i den aktuelle kørsel."
    elif shadow_ready:
        stage = "shadow_gate_ready"
        summary = "Reference Quality shadow har kandidater klar; næste skridt er validering mod production-gaten."
    elif fresh_rows:
        stage = "evidence_roles_missing"
        summary = "Der er en stor frisk Bet365-kandidatbase, men uafhængig ekstern markedsreference og modelreference mangler stadig."
    elif exact_rows:
        stage = "freshness_missing"
        summary = "Eksakte Bet365-kandidater findes, men prisfreshness stopper den aktuelle kørsel."
    elif fair_rows:
        stage = "exact_identity_missing"
        summary = "Fair probabilities findes, men kandidaterne mangler eksakt Bet365-identitet."
    else:
        stage = "candidate_feed_missing"
        summary = "Første stop er at få referencekandidater ind i feedet."

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "OBSERVABILITY_ONLY",
        "production_impact": "none",
        "stage": stage,
        "summary": summary,
        "current_decision": operational.get("decision"),
        "candidate_base": {
            "candidate_rows": candidate_rows,
            "fair_probability_rows": fair_rows,
            "exact_bet365_rows": exact_rows,
            "fresh_exact_bet365_rows": fresh_rows,
            "legacy_reference_depth_ready_rows": legacy_depth_rows,
            "reference_quality_shadow_ready_rows": shadow_ready,
            "qualified_now_rows": qualified_rows,
            "fresh_exact_share_of_candidates": pct(fresh_rows, candidate_rows),
            "shadow_ready_share_of_fresh_exact": pct(shadow_ready, fresh_exact_shadow),
        },
        "main_blockers": blockers,
        "near_term_unlock": {
            "required": ["external_market_reference", "model_reference"],
            "single_role_unlock_possible": bool(((rqg.get("unlock_priorities") or {}).get("recommended_next_unlock") or {}).get("single_role_unlock_possible")),
            "largest_market": first_market.get("market"),
            "largest_market_fresh_exact_candidates": int(first_market.get("fresh_exact_candidates") or 0),
            "potential_candidates_if_both_roles_added": fresh_exact_shadow,
            "note": "Potentiale er ikke et pick-estimat; edge/EV/stake-gates gælder stadig efter evidence-unlock.",
        },
        "market_priorities": markets[:5],
    }


def main():
    report = build_report(load_json(OPERATIONAL, {}), load_json(REFERENCE_QUALITY, {}))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "stage": report["stage"],
        "fresh_exact_bet365_rows": report["candidate_base"]["fresh_exact_bet365_rows"],
        "shadow_ready_rows": report["candidate_base"]["reference_quality_shadow_ready_rows"],
        "largest_market": report["near_term_unlock"]["largest_market"],
        "production_impact": report["production_impact"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
