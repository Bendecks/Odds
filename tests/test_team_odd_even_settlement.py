import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import model_settlement_fetch as s
class TeamOddEvenSettlementTests(unittest.TestCase):
 def row(self,market,pick):return {'event':'Home vs Away','market':market,'pick':pick}
 def test_home_odd_even(self):
  self.assertEqual(s.market_outcome(self.row('odd_even_home','odd'),(3,2)),'win')
  self.assertEqual(s.market_outcome(self.row('odd_even_home','even'),(3,2)),'loss')
 def test_away_odd_even(self):
  self.assertEqual(s.market_outcome(self.row('odd_even_away','even'),(3,2)),'win')
  self.assertEqual(s.market_outcome(self.row('odd_even_away','odd'),(3,2)),'loss')
 def test_supported(self):
  self.assertTrue(s.supported_market(self.row('odd_even_home','odd')))
  self.assertTrue(s.supported_market(self.row('odd_even_away','even')))
if __name__=='__main__':unittest.main()
