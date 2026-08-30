import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from model_validation_readiness import build

class ModelValidationReadinessTests(unittest.TestCase):
    def test_empty_history_is_not_promotion_ready(self):
        r=build([],[])
        self.assertFalse(r['promotion_ready'])
        self.assertEqual(r['settled_decisive_bets'],0)
        self.assertIsNone(r['roi_pct'])

    def test_computes_roi_clv_and_brier_from_new_model_settlements(self):
        signals=[{'decision':'PAPER PICK','model_version':'market-consensus-v3'}]
        settled=[{'result':'win','stake_dkk':1,'profit_dkk':1,'clv_pct':2,'fair_probability':0.6}]
        r=build(signals,settled)
        self.assertEqual(r['roi_pct'],100.0)
        self.assertEqual(r['mean_clv_pct'],2.0)
        self.assertAlmostEqual(r['brier_score'],0.16)
        self.assertFalse(r['promotion_ready'])

if __name__=='__main__': unittest.main()
