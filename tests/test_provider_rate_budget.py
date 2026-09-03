import pathlib, unittest

class ProviderRateBudgetTests(unittest.TestCase):
    def test_heavy_feed_and_settlement_schedules_do_not_share_hours(self):
        feed=pathlib.Path('.github/workflows/the_odds_feed.yml').read_text()
        settle=pathlib.Path('.github/workflows/model_settlement.yml').read_text()
        self.assertIn("cron: '17 */12 * * *'",feed)
        self.assertIn("cron: '37 2,8,14,20 * * *'",settle)

    def test_rate_limited_event_universe_degrades_without_stale_prices(self):
        src=pathlib.Path('scripts/odds_api_io_bet365.py').read_text()
        self.assertIn("'provider_unavailable':True",src)
        self.assertIn("OBS.write_text('')",src)
        self.assertIn('except requests.RequestException as exc:return unavailable',src)

    def test_hourly_closing_cap_leaves_headroom_for_heavy_feed(self):
        closing=pathlib.Path('.github/workflows/closing_price_capture.yml').read_text()
        feed=pathlib.Path('.github/workflows/the_odds_feed.yml').read_text()
        settle=pathlib.Path('.github/workflows/model_settlement.yml').read_text()
        self.assertIn('python scripts/odds_api_io_quota_budget.py feed --requested-calls 80',feed)
        self.assertIn('python scripts/odds_api_io_quota_budget.py closing --requested-calls 10',closing)
        self.assertIn('python scripts/odds_api_io_quota_budget.py settlement --requested-calls 20',settle)
        self.assertIn('output/odds_api_io_quota_budget.json',feed)
        self.assertIn('output/odds_api_io_quota_budget.json',closing)
        self.assertIn('output/odds_api_io_quota_budget.json',settle)

if __name__=='__main__':unittest.main()
