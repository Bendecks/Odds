import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import shadow_gate_analysis as s

class Bet365EventIdentityTests(unittest.TestCase):
 def test_exact_event_without_price_is_not_event_identity_failure(self):
  c={'bet365_event_id':'123','event_match_method':'exact'}
  self.assertEqual(s.identity_reason(c),'no_exact_bet365_price')
 def test_missing_exact_event_is_event_identity_failure(self):
  self.assertEqual(s.identity_reason({}),'event_identity')
  self.assertEqual(s.identity_reason({'bet365_event_id':'123','event_match_method':'diagnostic'}),'event_identity')
 def test_exact_verified_price_has_no_identity_failure(self):
  c={'bet365_event_id':'123','event_match_method':'exact','bet365_odds':2.0,'bet365_verified':True}
  self.assertIsNone(s.identity_reason(c))
if __name__=='__main__':unittest.main()
