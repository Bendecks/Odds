import unittest
from scripts.the_odds_feed import novig_fair

class TestReferenceFeedContract(unittest.TestCase):
    def test_two_way_market_normalizes(self):
        x=novig_fair([{'name':'A','price':1.8},{'name':'B','price':2.2}]); self.assertAlmostEqual(sum(x.values()),1.0)
    def test_invalid_single_outcome_has_no_fair_market(self):
        self.assertEqual(novig_fair([{'name':'A','price':2.0}]),{})

if __name__=='__main__':unittest.main()
