import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from closing_price_fetch import field_for, h2h_price

class ClosingPriceFetchTests(unittest.TestCase):
    def test_maps_exact_team_and_draw_picks(self):
        base={'event':'FC Copenhagen vs Brondby IF'}
        self.assertEqual(field_for({**base,'pick':'FC Copenhagen'}),'home')
        self.assertEqual(field_for({**base,'pick':'Brondby IF'}),'away')
        self.assertEqual(field_for({**base,'pick':'Draw'}),'draw')

    def test_does_not_guess_unknown_pick(self):
        self.assertIsNone(field_for({'event':'A vs B','pick':'C'}))

    def test_reads_only_bet365_h2h_family(self):
        data={'bookmakers':{'Bet365':[{'name':'Totals','odds':[{'over':1.9,'under':1.9}]},{'name':'ML','updatedAt':'t','odds':[{'home':2.0,'draw':3.0,'away':4.0}]}]}}
        self.assertEqual(h2h_price(data,'away'),(4.0,'t'))

    def test_missing_price_returns_none(self):
        self.assertEqual(h2h_price({'bookmakers':{}},'home'),(None,None))

if __name__=='__main__':unittest.main()
