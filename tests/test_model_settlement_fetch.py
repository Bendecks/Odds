import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from model_settlement_fetch import outcome

class ModelSettlementFetchTests(unittest.TestCase):
    def row(self,pick='A'):return {'event':'A vs B','pick':pick,'market':'h2h'}
    def test_home_win(self):self.assertEqual(outcome(self.row('A'),{'status':'settled','scores':{'home':2,'away':1}}),'win')
    def test_away_loss(self):self.assertEqual(outcome(self.row('B'),{'status':'settled','scores':{'home':2,'away':1}}),'loss')
    def test_draw_pick(self):self.assertEqual(outcome(self.row('Draw'),{'status':'settled','scores':{'home':1,'away':1}}),'win')
    def test_cancelled_is_void(self):self.assertEqual(outcome(self.row(),{'status':'cancelled'}),'void')
    def test_pending_is_not_settled(self):self.assertIsNone(outcome(self.row(),{'status':'pending','scores':{'home':0,'away':0}}))
    def test_unknown_pick_is_not_guessed(self):self.assertIsNone(outcome(self.row('C'),{'status':'settled','scores':{'home':1,'away':0}}))

if __name__=='__main__':unittest.main()
