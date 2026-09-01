import math,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import derived_goal_markets as d

class TeamOddEvenTests(unittest.TestCase):
 def test_probabilities_sum_to_one(self):
  for lam in (.2,1.0,2.5,4.0):
   p=d.odd_even_probabilities(lam);self.assertAlmostEqual(p['odd']+p['even'],1.0,12)
 def test_known_poisson_even_probability(self):
  p=d.odd_even_probabilities(1.0)
  self.assertAlmostEqual(p['even'],(1+math.exp(-2))/2,12)
 def test_goal_markets_use_team_lambdas(self):
  p=d.goal_market_probabilities(1.2,.8)
  self.assertEqual(p['odd_even_home'],d.odd_even_probabilities(1.2))
  self.assertEqual(p['odd_even_away'],d.odd_even_probabilities(.8))
  self.assertEqual(p['odd_even'],d.odd_even_probabilities(2.0))
if __name__=='__main__':unittest.main()
