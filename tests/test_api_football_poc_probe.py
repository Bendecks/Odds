import json
import os
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import api_football_poc_probe as probe


class ApiFootballPocProbeTests(unittest.TestCase):
    def test_missing_key_fails_soft_without_production_impact(self):
        old_env = {name: os.environ.get(name) for name in probe.SECRET_NAMES}
        for name in probe.SECRET_NAMES:
            os.environ.pop(name, None)
        try:
            report = probe.build_report([probe.missing_key_report()], None)
        finally:
            for name, value in old_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        self.assertFalse(report["configured"])
        self.assertFalse(report["ok"])
        self.assertEqual(report["mode"], "SHADOW_ONLY")
        self.assertEqual(report["production_impact"], "none")
        self.assertEqual(report["reference_quality_role_if_promoted"], "external_market_reference")

    def test_provenance_contract_uses_bookmaker_economic_source(self):
        contract = probe.provenance_contract()
        self.assertEqual(contract["transport_provider_id"], "api-sports:api-football")
        self.assertEqual(contract["evidence_family"], "external_market_price")
        self.assertIn("<bookmaker_id>", contract["economic_source_id"])

    def test_api_errors_make_successful_http_response_not_ok(self):
        entries = [{
            "endpoint": "/odds/bookmakers",
            "configured": True,
            "ok": False,
            "status_code": 200,
            "errors": {"access": "Your account is suspended"},
            "results": 0,
            "sample": [],
        }]
        report = probe.build_report(entries, "API_FOOTBALL_KEY")
        self.assertFalse(report["ok"])
        self.assertEqual(report["account_status"], "access_error")

    def test_main_writes_status_files_without_secret(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            old_out = (probe.OUT, probe.STATUS_JSON, probe.STATUS_MD)
            old_env = {name: os.environ.get(name) for name in probe.SECRET_NAMES}
            for name in probe.SECRET_NAMES:
                os.environ.pop(name, None)
            probe.OUT = root
            probe.STATUS_JSON = root / "api_football_poc_status.json"
            probe.STATUS_MD = root / "api_football_poc_status.md"
            try:
                probe.main()
                data = json.loads(probe.STATUS_JSON.read_text())
            finally:
                probe.OUT, probe.STATUS_JSON, probe.STATUS_MD = old_out
                for name, value in old_env.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
            self.assertEqual(data["provider"], "API-Football / API-Sports")
            self.assertFalse(data["configured"])
            self.assertTrue(probe.STATUS_MD.name.endswith(".md"))


if __name__ == "__main__":
    unittest.main()
