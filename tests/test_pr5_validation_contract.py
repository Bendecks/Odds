import pathlib, unittest

class TestPR5ValidationContract(unittest.TestCase):
    def test_required_diagnostic_outputs_are_committed(self):
        w=pathlib.Path('.github/workflows/the_odds_feed.yml').read_text()
        self.assertIn('output/reference_match_diagnostics.json',w)
        self.assertIn('output/market_signal_inventory.json',w)
        self.assertIn('retention-days: 30',w)

if __name__=='__main__':unittest.main()
