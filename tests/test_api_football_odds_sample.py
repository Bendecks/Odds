import json
import os
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import api_football_odds_sample as sample


class ApiFootballOddsSampleTests(unittest.TestCase):
    def test_selects_external_bookmakers_and_target_bets(self):
        bookmakers = [
            {"id": 4, "name": "Bet365"},
            {"id": 3, "name": "Betfair"},
            {"id": 2, "name": "Marathonbet"},
        ]
        bets = [
            {"id": 1, "name": "Match Winner"},
            {"id": 5, "name": "Goals Over/Under"},
            {"id": 8, "name": "Both Teams Score"},
        ]
        selected_books = sample.pick_bookmakers(bookmakers)
        selected_bets = sample.pick_bets(bets)
        self.assertEqual([row["name"] for row in selected_books], ["Betfair", "Marathonbet"])
        self.assertEqual([row["market"] for row in selected_bets], ["h2h", "totals", "btts"])

    def test_bookmaker_selection_falls_back_to_external_catalog_rows(self):
        bookmakers = [
            {"id": 4, "name": "Bet365"},
            {"id": 9, "name": "LocalBook"},
            {"id": 10, "name": "AnotherBook"},
        ]
        self.assertEqual(
            sample.pick_bookmakers(bookmakers),
            [{"id": 9, "name": "LocalBook"}, {"id": 10, "name": "AnotherBook"}],
        )

    def test_candidate_dates_prefer_verified_exact_candidate_dates(self):
        rows = [
            {"commence_time": "2026-09-07T12:00:00Z", "bet365_verified": True, "event_match_method": "exact"},
            {"commence_time": "2026-09-07T18:00:00Z", "bet365_verified": True, "event_match_method": "exact"},
            {"commence_time": "2026-09-08T18:00:00Z", "bet365_verified": True, "event_match_method": "exact"},
            {"commence_time": "2026-09-09T18:00:00Z", "bet365_verified": False, "event_match_method": "exact"},
        ]
        self.assertEqual(sample.candidate_dates(rows), ["2026-09-07", "2026-09-08"])

    def test_build_report_is_shadow_only_and_keeps_promotion_blockers(self):
        report = sample.build_report(
            "API_FOOTBALL_KEY",
            [{"id": 3, "name": "Betfair"}],
            [{"id": 1, "name": "Match Winner"}],
            [{"ok": True, "fixtures_returned": 2, "selection_observations": 6}],
            ["2026-09-07"],
            [{"id": 3, "name": "Betfair"}],
            [{"market": "h2h", "id": 1, "name": "Match Winner"}],
            {
                "bookmakers": {"endpoint": "/odds/bookmakers", "ok": True, "status_code": 200, "results": 1, "headers": {}, "errors": [], "body": {"response": [{"id": 3, "name": "Betfair"}]}},
                "bets": {"endpoint": "/odds/bets", "ok": True, "status_code": 200, "results": 1, "headers": {}, "errors": [], "body": {"response": [{"id": 1, "name": "Match Winner"}]}},
            },
        )
        self.assertEqual(report["mode"], "SHADOW_ONLY")
        self.assertEqual(report["production_impact"], "none")
        self.assertTrue(report["coverage"]["has_external_market_sample"])
        self.assertIn("economic_source_id", report["provenance_template"])
        self.assertTrue(report["promotion_blockers"])
        self.assertEqual(report["catalogs"]["diagnostics"]["bookmakers"]["items_parsed"], 1)

    def test_main_writes_report_without_secret(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            old = (sample.OUT, sample.STATUS_JSON, sample.STATUS_MD)
            old_env = {name: os.environ.get(name) for name in sample.SECRET_NAMES}
            for name in sample.SECRET_NAMES:
                os.environ.pop(name, None)
            sample.OUT = root
            sample.STATUS_JSON = root / "sample.json"
            sample.STATUS_MD = root / "sample.md"
            try:
                sample.main()
                data = json.loads(sample.STATUS_JSON.read_text())
            finally:
                sample.OUT, sample.STATUS_JSON, sample.STATUS_MD = old
                for name, value in old_env.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
            self.assertFalse(data["configured"])
            self.assertEqual(data["coverage"]["odds_calls"], 0)


if __name__ == "__main__":
    unittest.main()
