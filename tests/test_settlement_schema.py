import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from settlement_schema import signal_key, valid_settlement, profit_dkk, clv_pct

class SettlementSchemaTests(unittest.TestCase):
    def base(self):return {'event':'A vs B','market':'h2h','pick':'A','price_timestamp':'2026-08-30T12:00:00Z','model_version':'v1','odds':2.0,'stake_dkk':1.5}
    def test_signal_identity_stable(self):
        a=self.base();b={**a,'odds':2.2};self.assertEqual(signal_key(a),signal_key(b))
    def test_win_profit(self):
        x={**self.base(),'signal_key':'x','result':'WIN'};self.assertTrue(valid_settlement(x));self.assertEqual(profit_dkk(x),1.5)
    def test_loss_profit(self):
        x={**self.base(),'signal_key':'x','result':'loss'};self.assertEqual(profit_dkk(x),-1.5)
    def test_clv_decimal_odds(self):
        x={**self.base(),'closing_odds':1.8};self.assertAlmostEqual(clv_pct(x),11.1111,4)
    def test_rejects_unknown_result(self):
        self.assertFalse(valid_settlement({**self.base(),'signal_key':'x','result':'pending'}))
if __name__=='__main__':unittest.main()
