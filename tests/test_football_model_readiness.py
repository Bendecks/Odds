import json
import pathlib
import tempfile
import unittest

import sys
sys.path.insert(0, "scripts")
import football_model_readiness as model


class FootballModelReadinessTests(unittest.TestCase):
    def test_reports_metadata_and_first_model_scope(self):
        candidates = [
            {
                "event": "Home FC vs Away FC",
                "market": "h2h",
                "sport": "football",
                "league": "Premier League",
                "bet365_verified": True,
                "event_match_method": "exact",
            },
            {
                "event": "Home FC vs Away FC",
                "market": "totals",
                "sport": "football",
                "league": "Premier League",
                "bet365_verified": True,
                "event_match_method": "exact",
            },
            {
                "event": "Home FC vs Away FC",
                "market": "spreads",
                "sport": "football",
                "league": "Premier League",
            },
        ]
        rqg = {
            "unlock_priorities": {
                "market_priorities": [
                    {"market": "h2h", "fresh_exact_candidates": 1},
                    {"market": "totals", "fresh_exact_candidates": 1},
                ]
            }
        }
        report = model.build_report(candidates, rqg)
        self.assertEqual(report["mode"], "SHADOW_ONLY")
        self.assertEqual(report["production_impact"], "none")
        self.assertEqual(report["reference_quality_role_if_promoted"], "model_reference")
        self.assertEqual(report["metadata"]["league_coverage"], 1.0)
        self.assertEqual(report["market_scope"]["first_model_scope_rows"], 2)
        self.assertEqual(report["league_mapping"]["public_data_hints"]["football-data.co.uk:E0"], 3)
        self.assertIn("historical_results_adapter_not_yet_built", report["blockers"])

    def test_missing_metadata_fails_closed(self):
        report = model.build_report([{"event": "A vs B", "market": "h2h"}], {})
        self.assertEqual(report["metadata"]["sport_coverage"], 0)
        self.assertEqual(report["metadata"]["league_coverage"], 0)
        self.assertEqual(report["market_scope"]["first_model_scope_rows"], 0)
        self.assertIn("candidate_league_metadata_missing_until_next_feed", report["blockers"])
        self.assertIn("public_data_league_mapping_not_verified", report["blockers"])
        self.assertEqual(report["missing_by_market"]["h2h"]["league_missing"], 1)

    def test_main_writes_public_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            candidates = root / "candidates.json"
            rqg = root / "rqg.json"
            out = root / "football_model_readiness.json"
            candidates.write_text(json.dumps([{"event": "A vs B", "market": "h2h"}]))
            rqg.write_text(json.dumps({}))
            old = (model.CANDIDATES, model.REFERENCE_QUALITY, model.OUT)
            model.CANDIDATES, model.REFERENCE_QUALITY, model.OUT = candidates, rqg, out
            try:
                model.main()
                data = json.loads(out.read_text())
            finally:
                model.CANDIDATES, model.REFERENCE_QUALITY, model.OUT = old
            self.assertEqual(data["production_impact"], "none")
            self.assertIn("metadata", data)


if __name__ == "__main__":
    unittest.main()
