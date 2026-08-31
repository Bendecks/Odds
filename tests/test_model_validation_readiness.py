import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from model_validation_readiness import build, roi_ci, calibration

class ModelValidationReadinessTests(unittest.TestCase):
    def test_empty_history_is_not_promotion_ready(self):
        r=build([],[]);self.assertFalse(r['promotion_ready']);self.assertEqual(r['settled_decisive_bets'],0);self.assertIsNone(r['roi_pct']);self.assertIsNone(r['roi_bootstrap_95_pct']);self.assertIsNone(r['expected_calibration_error'])

    def test_computes_roi_clv_and_brier_from_new_model_settlements(self):
        signals=[{'decision':'PAPER PICK','model_version':'market-consensus-v3'}]
        settled=[{'signal_key':'A|h2h|A|t|v3','result':'win','stake_dkk':1,'odds':2.0,'closing_odds':2.0,'fair_probability':0.6,'model_version':'market-consensus-v3'}]
        r=build(signals,settled)
        self.assertEqual(r['roi_pct'],100.0);self.assertEqual(r['mean_clv_pct'],0.0);self.assertAlmostEqual(r['brier_score'],0.16);self.assertAlmostEqual(r['expected_calibration_error'],0.4);self.assertFalse(r['promotion_ready']);self.assertEqual(r['current_model_version'],'market-consensus-v3')

    def test_bootstrap_roi_interval_is_deterministic(self):
        settled=[{'signal_key':'a','result':'win','stake_dkk':1,'odds':2.0},{'signal_key':'b','result':'loss','stake_dkk':1,'odds':2.0},{'signal_key':'c','result':'win','stake_dkk':1,'odds':2.2}]
        self.assertEqual(roi_ci(settled),roi_ci(settled));self.assertEqual(len(roi_ci(settled)),2)

    def test_calibration_bins_compare_prediction_with_outcome(self):
        rows=[{'result':'win','fair_probability':.62},{'result':'loss','fair_probability':.68}]
        bins,ece=calibration(rows);self.assertEqual(bins[0]['bucket'],'0.6-0.7');self.assertEqual(bins[0]['n'],2);self.assertEqual(bins[0]['actual_win_rate'],.5);self.assertAlmostEqual(ece,.15)

    def test_separates_settlement_metrics_by_model_version(self):
        settled=[{'signal_key':'a','result':'win','stake_dkk':1,'odds':2.0,'model_version':'v3'},{'signal_key':'b','result':'loss','stake_dkk':1,'odds':2.0,'model_version':'v4'}]
        r=build([],settled);self.assertEqual(r['settlement_metrics_by_model_version']['v3']['settled_decisive_bets'],1);self.assertEqual(r['settlement_metrics_by_model_version']['v4']['settled_decisive_bets'],1)

    def test_invalid_legacy_shaped_row_is_excluded(self):
        r=build([], [{'result':'win','stake_dkk':1,'profit_dkk':99}])
        self.assertEqual(r['valid_settlements'],0);self.assertIsNone(r['roi_pct'])
if __name__=='__main__':unittest.main()
