import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from settlement_schema import clv_pct

class ClosingPriceTests(unittest.TestCase):
    def test_positive_clv_when_taken_price_beats_close(self):self.assertAlmostEqual(clv_pct({'odds':2.2,'closing_odds':2.0}),10.0)
    def test_negative_clv_when_market_drifts(self):self.assertAlmostEqual(clv_pct({'odds':1.8,'closing_odds':2.0}),-10.0)
    def test_invalid_close_has_no_clv(self):self.assertIsNone(clv_pct({'odds':2,'closing_odds':1}))
if __name__=='__main__':unittest.main()
