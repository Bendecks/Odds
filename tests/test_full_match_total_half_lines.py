import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import derived_goal_markets as g
import derived_market_join as j
import model_settlement_fetch as s

class FullMatchTotalHalfLineTests(unittest.TestCase):
 def test_probabilities_sum_to_one(self):
  for line in (0.5,1.5,2.5,3.5,4.5,5.5,6.5):
   p=g.half_line_probabilities(2.7,line)
   self.assertAlmostEqual(p['over']+p['under'],1.0,places=12)
 def test_known_over_half_probability(self):
  p=g.half_line_probabilities(2.0,0.5)
  self.assertAlmostEqual(p['over'],1.0-__import__('math').exp(-2.0),places=12)
 def test_rejects_non_half_lines(self):
  for line in (0,1,1.25,-0.5):
   with self.assertRaises(ValueError):g.half_line_probabilities(2.5,line)
 def test_join_guard_requires_semantics(self):
  self.assertTrue(j.valid_half_line_candidate({'line':2.5,'market_semantics':'binary_half_line_no_push'}))
  self.assertFalse(j.valid_half_line_candidate({'line':2.5}))
 def test_total_goals_settlement(self):
  row={'event':'A vs B','market':'total_goals','pick':'over','line':2.5}
  self.assertEqual(s.market_outcome(row,(2,1)),'win')
  row['pick']='under';self.assertEqual(s.market_outcome(row,(1,1)),'win')
 def test_total_goals_non_half_line_fails_closed(self):
  row={'event':'A vs B','market':'total_goals','pick':'over','line':2.0}
  self.assertIsNone(s.market_outcome(row,(2,1)))

if __name__=='__main__':unittest.main()
