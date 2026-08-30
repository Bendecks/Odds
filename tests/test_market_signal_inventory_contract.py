import pathlib, unittest

class TestMarketSignalInventoryContract(unittest.TestCase):
    def test_inventory_does_not_filter_to_core_markets(self):
        src=pathlib.Path('scripts/market_signal_candidates.py').read_text()
        self.assertNotIn("if m not in CORE",src)
        self.assertIn("'unmodelled'",src)

if __name__=='__main__':unittest.main()
