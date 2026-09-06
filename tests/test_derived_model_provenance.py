import pathlib
import sys
import unittest
from datetime import datetime, timedelta, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import derived_btts_model as btts
import derived_goal_markets as goals
import reference_quality_shadow as rqg


NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


def source(economic, family="market_price", transport="odds-api.io", version="test-v1"):
    return {
        "transport_provider_id": transport,
        "economic_source_id": economic,
        "evidence_family": family,
        "model_or_feed_version": version,
    }


def row(market, pick, probability, line=None):
    item = {
        "event": "Home FC vs Away FC",
        "event_id": "evt1",
        "sport": "soccer_test",
        "commence_time": "2026-09-06T12:30:00Z",
        "market": market,
        "pick": pick,
        "fair_probability": probability,
        "books": 4,
        "bet365_event_id": "bet365-evt1",
        "event_match_method": "exact",
        "reference_sources": [
            source("unibet"),
            source("api-football:bookmaker-x"),
        ],
    }
    if line is not None:
        item["line"] = line
    return item


def model_input_rows():
    return [
        row("h2h", "Home FC", 0.46),
        row("h2h", "Draw", 0.27),
        row("h2h", "Away FC", 0.27),
        row("totals", "Over", 0.52, 2.5),
        row("totals", "Under", 0.48, 2.5),
    ]


class DerivedModelProvenanceTests(unittest.TestCase):
    def test_btts_rows_include_market_derived_provenance(self):
        out = btts.derive_for_event(model_input_rows())
        self.assertTrue(out)
        for item in out:
            sources = item["reference_sources"]
            economics = {s["economic_source_id"] for s in sources}
            self.assertIn("unibet", economics)
            self.assertIn("api-football:bookmaker-x", economics)
            self.assertIn("derived:market-consensus-poisson", economics)
            derived = next(s for s in sources if s["economic_source_id"] == "derived:market-consensus-poisson")
            self.assertEqual(derived["evidence_family"], "derived_probability")
            self.assertEqual(derived["model_or_feed_version"], btts.MODEL_VERSION)

    def test_goal_rows_reuse_same_derived_provenance_contract(self):
        out = goals.derive_for_event(model_input_rows())
        self.assertTrue(out)
        derived = next(
            s for s in out[0]["reference_sources"]
            if s["economic_source_id"] == "derived:market-consensus-poisson"
        )
        self.assertEqual(derived["transport_provider_id"], "local-derived-market-model")
        self.assertEqual(derived["model_or_feed_version"], goals.MODEL_VERSION)

    def test_market_derived_probability_does_not_satisfy_independent_model_role(self):
        item = btts.derive_for_event(model_input_rows())[0]
        item.update({
            "bet365_odds": 2.0,
            "bet365_verified": True,
            "bet365_timestamp": (NOW - timedelta(minutes=5)).isoformat(),
        })
        evaluated = rqg.evaluate_candidate(item, NOW)
        self.assertFalse(evaluated["shadow_ready"])
        self.assertIn("unibet_reference", evaluated["roles_present"])
        self.assertIn("external_market_reference", evaluated["roles_present"])
        self.assertNotIn("model_reference", evaluated["roles_present"])
        self.assertIn("missing_model_reference", evaluated["failure_reasons"])


if __name__ == "__main__":
    unittest.main()
