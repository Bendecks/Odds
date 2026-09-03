import sys
import unittest

sys.path.insert(0, "scripts")
import odds_api_io_quota_budget as budget


class OddsApiIoQuotaBudgetTests(unittest.TestCase):
    def test_budget_holds_reserve_when_remaining_header_exists(self):
        status = {
            "apis": [
                {
                    "api": "odds-api.io",
                    "configured": True,
                    "ok": True,
                    "headers": {"x-requests-remaining": "90"},
                }
            ]
        }
        result = budget.budget_for("feed", requested=80, reserve=40, status=status)
        self.assertEqual(result["allowed_calls"], 50)
        self.assertEqual(result["remaining_calls"], 90)
        self.assertEqual(result["mode"], "quota_aware")

    def test_budget_never_goes_negative(self):
        status = {"apis": [{"api": "odds-api.io", "headers": {"ratelimit-remaining": "12"}}]}
        result = budget.budget_for("settlement", requested=20, reserve=30, status=status)
        self.assertEqual(result["allowed_calls"], 0)

    def test_missing_quota_header_keeps_existing_cap(self):
        status = {"apis": [{"api": "odds-api.io", "configured": True, "ok": True, "headers": {}}]}
        result = budget.budget_for("closing", requested=10, reserve=25, status=status)
        self.assertEqual(result["allowed_calls"], 10)
        self.assertIsNone(result["remaining_calls"])
        self.assertEqual(result["mode"], "default_cap_no_quota_header")

    def test_ignores_the_odds_api_headers(self):
        status = {
            "apis": [
                {"api": "the-odds-api", "headers": {"x-requests-remaining": "999"}},
                {"api": "odds-api.io", "headers": {"x-ratelimit-remaining": "45"}},
            ]
        }
        result = budget.budget_for("feed", requested=80, reserve=40, status=status)
        self.assertEqual(result["remaining_calls"], 45)
        self.assertEqual(result["allowed_calls"], 5)


if __name__ == "__main__":
    unittest.main()
