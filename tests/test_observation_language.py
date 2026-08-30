import pathlib, unittest

class TestObservationLanguage(unittest.TestCase):
    def test_broad_market_script_outputs_inventory_not_bets(self):
        src=pathlib.Path('scripts/market_signal_candidates.py').read_text()
        self.assertIn("'inventory':inventory",src)
        self.assertNotIn("'decision':'PLAY'",src)

if __name__=='__main__':unittest.main()
