import pathlib
import sys
import unittest
from datetime import datetime, timezone, timedelta


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reference_quality_shadow as rqg


NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


def source(economic, family="market_price", transport="odds-api.io", version="test-v1"):
    return {
        "transport_provider_id": transport,
        "economic_source_id": economic,
        "evidence_family": family,
        "model_or_feed_version": version,
    }


def candidate(*sources, **extra):
    row = {
        "event": "A vs B",
        "event_id": "ref-1",
        "bet365_event_id": "bet-1",
        "market": "h2h",
        "pick": "A",
        "fair_probability": 0.55,
        "bet365_odds": 2.0,
        "bet365_verified": True,
        "event_match_method": "exact",
        "bet365_timestamp": (NOW - timedelta(minutes=5)).isoformat(),
        "reference_sources": list(sources),
    }
    row.update(extra)
    return row


class ReferenceQualityShadowTests(unittest.TestCase):
    def test_unibet_only_is_not_shadow_ready(self):
        row = rqg.evaluate_candidate(candidate(source("unibet")), NOW)
        self.assertFalse(row["shadow_ready"])
        self.assertIn("unibet_reference", row["roles_present"])
        self.assertIn("missing_external_market_reference", row["failure_reasons"])
        self.assertIn("missing_model_reference", row["failure_reasons"])

    def test_bet365_reference_is_ignored(self):
        row = rqg.evaluate_candidate(candidate(source("unibet"), source("bet365")), NOW)
        self.assertIn("bet365", row["ignored_economic_sources"])
        self.assertNotIn("bet365", row["independent_economic_sources"])
        self.assertIn("missing_external_market_reference", row["failure_reasons"])

    def test_missing_provenance_fails_closed(self):
        row = rqg.evaluate_candidate(candidate({"economic_source_id": "api-football"}), NOW)
        self.assertFalse(row["shadow_ready"])
        self.assertIn("missing_reference_provenance", row["failure_reasons"])

    def test_unibet_external_and_model_can_pass_shadow_gate(self):
        row = rqg.evaluate_candidate(candidate(
            source("unibet"),
            source("api-football:bookmaker-x"),
            source("model:dixon-coles-elo", family="football_model", transport="local-model"),
        ), NOW)
        self.assertTrue(row["shadow_ready"])
        self.assertEqual(row["missing_roles"], [])

    def test_report_summarises_missing_roles_by_market(self):
        report = rqg.build_report([
            candidate(source("unibet"), market="h2h"),
            candidate(source("unibet"), market="totals"),
        ], NOW)
        self.assertEqual(report["mode"], "SHADOW_ONLY")
        self.assertEqual(report["production_impact"], "none")
        self.assertEqual(report["fresh_exact_candidates"], 2)
        self.assertEqual(report["shadow_ready_candidates"], 0)
        self.assertEqual(report["missing_roles"]["external_market_reference"], 2)
        self.assertEqual(report["by_market"]["h2h"]["missing_roles"]["model_reference"], 1)


if __name__ == "__main__":
    unittest.main()
