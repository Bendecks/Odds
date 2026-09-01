import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import model_settlement_fetch as s

class IntegerScoreSettlementTests(unittest.TestCase):
 def test_non_integer_score_is_rejected(self):
  self.assertIsNone(s.integer_score_pair((1.5,1.0)))
 def test_integer_score_is_normalized(self):
  self.assertEqual(s.integer_score_pair((2.0,1.0)),(2,1))
 def test_provider_non_integer_score_is_missing(self):
  event={'status':'finished','scores':{'home':2.5,'away':1}}
  self.assertEqual(s.settlement_score_pair(event),(None,'missing_score'))
 def test_valid_odd_even_still_settles(self):
  row={'event':'A vs B','market':'odd_even','pick':'odd'}
  self.assertEqual(s.market_outcome(row,(2,1)),'win')
 def test_non_integer_market_outcome_fails_closed(self):
  row={'event':'A vs B','market':'odd_even','pick':'odd'}
  self.assertIsNone(s.market_outcome(row,(1.5,1)))

if __name__=='__main__':unittest.main()
