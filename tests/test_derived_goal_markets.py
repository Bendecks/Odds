import math, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import derived_goal_markets as m

class DerivedGoalMarketTests(unittest.TestCase):
    def test_exact_goal_probability(self):
        self.assertAlmostEqual(m.exact_goal_probability(2.0,0),math.exp(-2.0))
        self.assertAlmostEqual(m.exact_goal_probability(2.0,2),2.0*math.exp(-2.0))

    def test_binary_markets_sum_to_one(self):
        x=m.goal_market_probabilities(1.6,1.1)
        for market in ('odd_even','clean_sheet_home','clean_sheet_away'):
            self.assertAlmostEqual(sum(x[market].values()),1.0)

    def test_clean_sheet_uses_opponent_lambda(self):
        x=m.goal_market_probabilities(1.7,0.8)
        self.assertAlmostEqual(x['clean_sheet_home']['yes'],math.exp(-0.8))
        self.assertAlmostEqual(x['clean_sheet_away']['yes'],math.exp(-1.7))

    def test_exact_goal_rows_are_valid_probabilities(self):
        x=m.goal_market_probabilities(1.4,1.2)
        for market in ('exact_total_goals','home_exact_goals','away_exact_goals'):
            self.assertTrue(all(0 < p < 1 for p in x[market].values()))
            self.assertLess(sum(x[market].values()),1.000001)

if __name__=='__main__':unittest.main()
