import importlib.util, pathlib, unittest

SPEC=importlib.util.spec_from_file_location('derived_btts_model',pathlib.Path('scripts/derived_btts_model.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


def row(market,pick,p,line=None,books=4):
 r={'event':'Home FC vs Away FC','event_id':'evt1','sport':'soccer_test','commence_time':'2026-09-01T12:00:00Z','market':market,'pick':pick,'fair_probability':p,'books':books}
 if line is not None:r['line']=line
 return r


class DerivedBttsModelTests(unittest.TestCase):
 def test_poisson_probability_is_bounded(self):
  *_,btts=M.model_probs(1.5,1.1)
  self.assertGreater(btts,0);self.assertLess(btts,1)

 def test_derives_yes_and_no_from_quality_inputs(self):
  rows=[row('h2h','Home FC',0.46),row('h2h','Draw',0.27),row('h2h','Away FC',0.27),row('totals','Over',0.52,2.5),row('totals','Under',0.48,2.5)]
  out=M.derive_for_event(rows)
  self.assertEqual([x['pick'] for x in out],['yes','no'])
  self.assertAlmostEqual(sum(x['fair_probability'] for x in out),1.0,places=5)
  self.assertTrue(all(x['model_fit_rmse']<=M.MAX_RMSE for x in out))
  self.assertTrue(all(x['model_inputs']=='1x2_consensus+totals_2.5_consensus' for x in out))

 def test_rejects_shallow_reference_depth(self):
  rows=[row('h2h','Home FC',0.46,books=2),row('h2h','Draw',0.27,books=2),row('h2h','Away FC',0.27,books=2),row('totals','Over',0.52,2.5,2),row('totals','Under',0.48,2.5,2)]
  self.assertEqual(M.derive_for_event(rows),[])

 def test_rejects_missing_two_point_five_total(self):
  rows=[row('h2h','Home FC',0.46),row('h2h','Draw',0.27),row('h2h','Away FC',0.27),row('totals','Over',0.52,3.5),row('totals','Under',0.48,3.5)]
  self.assertEqual(M.derive_for_event(rows),[])

if __name__=='__main__':unittest.main()
