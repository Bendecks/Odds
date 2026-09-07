import datetime
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import sys
sys.path.insert(0, "scripts")
import public_football_data_probe as probe


CSV_SAMPLE = """Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR
E0,14/08/26,Home FC,Away FC,2,1,H
E0,15/08/26,Other FC,Third FC,,,
"""


class PublicFootballDataProbeTests(unittest.TestCase):
    def test_season_code_uses_football_season_boundary(self):
        self.assertEqual(probe.season_code(datetime.date(2026, 9, 7)), "2627")
        self.assertEqual(probe.season_code(datetime.date(2026, 5, 1)), "2526")

    def test_parse_csv_requires_match_result_columns(self):
        parsed = probe.parse_csv(CSV_SAMPLE)
        self.assertEqual(parsed["missing_required_columns"], [])
        self.assertEqual(parsed["row_count"], 2)
        self.assertEqual(parsed["parseable_rows"], 2)
        self.assertEqual(parsed["completed_result_rows"], 1)
        self.assertEqual(parsed["sample"][0]["home"], "Home FC")

    def test_probe_league_reports_ready_csv(self):
        response = mock.Mock()
        response.status = 200
        response.headers = {"content-type": "text/csv"}
        response.read.return_value = CSV_SAMPLE.encode("utf-8")
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=None)
        with mock.patch("urllib.request.urlopen", return_value=response):
            row = probe.probe_league("2627", {"code": "E0", "country": "England", "league": "Premier League"})
        self.assertTrue(row["ok"])
        self.assertEqual(row["status_code"], 200)
        self.assertEqual(row["row_count"], 2)

    def test_build_report_is_shadow_only(self):
        report = probe.build_report([
            {"ok": True, "league": "Premier League", "code": "E0"},
            {"ok": False, "league": "Bundesliga", "code": "D1"},
        ], "2627")
        self.assertEqual(report["mode"], "SHADOW_ONLY")
        self.assertEqual(report["production_impact"], "none")
        self.assertEqual(report["source_status"], "ok")
        self.assertEqual(report["leagues_data_ready"], 1)
        self.assertTrue(report["has_any_valid_league"])

    def test_main_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            old = (probe.OUT, probe.STATUS_JSON, probe.STATUS_MD, probe.LEAGUES)
            probe.OUT = root
            probe.STATUS_JSON = root / "public_football_data_probe.json"
            probe.STATUS_MD = root / "public_football_data_probe.md"
            probe.LEAGUES = [{"code": "E0", "country": "England", "league": "Premier League"}]
            try:
                with mock.patch.object(probe, "probe_league", return_value={"ok": True, "code": "E0", "league": "Premier League"}):
                    probe.main()
                data = json.loads(probe.STATUS_JSON.read_text())
                md_text = probe.STATUS_MD.read_text()
            finally:
                probe.OUT, probe.STATUS_JSON, probe.STATUS_MD, probe.LEAGUES = old
        self.assertEqual(data["provider"], "Football-Data.co.uk")
        self.assertIn("Public football data probe", md_text)


if __name__ == "__main__":
    unittest.main()
