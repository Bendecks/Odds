import pathlib
import sys
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

sys.modules.setdefault("requests", types.SimpleNamespace(RequestException=Exception, HTTPError=Exception))
import odds_api_io_bootstrap as bootstrap


class ProviderMetadataDiagnosticsTests(unittest.TestCase):
    def test_summarises_event_metadata_without_extra_provider_calls(self):
        events = [
            {
                "id": "1",
                "home": "A",
                "away": "B",
                "sport": "football",
                "league": "Denmark Superliga",
                "date": "2026-09-07T18:00:00Z",
            },
            {
                "id": "2",
                "home": "C",
                "away": "D",
                "date": "2026-09-07T19:00:00Z",
            },
        ]
        report = bootstrap.provider_event_metadata(events, [events[0]])
        self.assertEqual(report["events_total"], 2)
        self.assertEqual(report["prioritized_events"], 1)
        self.assertEqual(report["rows_with_sport"], 1)
        self.assertEqual(report["rows_with_league"], 1)
        self.assertEqual(report["prioritized_with_sport"], 1)
        self.assertEqual(report["prioritized_with_league"], 1)
        self.assertEqual(report["top_leagues"], [("Denmark Superliga", 1)])
        self.assertIn(("id", 2), report["event_key_counts"])
        self.assertEqual(report["samples"][0]["keys"], sorted(events[0].keys()))

    def test_handles_missing_or_non_list_payloads(self):
        report = bootstrap.provider_event_metadata(None, [])
        self.assertEqual(report["events_total"], 0)
        self.assertEqual(report["top_sports"], [])
        self.assertEqual(report["samples"], [])


if __name__ == "__main__":
    unittest.main()
