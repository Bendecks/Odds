import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from derived_btts_model import exact_event_identity

class DerivedEventIdentityTests(unittest.TestCase):
 def test_preserves_exact_identity_from_any_source_row(self):
  rows=[{}, {'bet365_event_id':'abc123','event_match_method':'exact','bet365_verified':False}]
  self.assertEqual(exact_event_identity(rows),{'bet365_event_id':'abc123','event_match_method':'exact'})
 def test_does_not_promote_diagnostic_identity(self):
  rows=[{'bet365_event_id':'abc123','event_match_method':'diagnostic'}]
  self.assertEqual(exact_event_identity(rows),{})
 def test_does_not_copy_price_or_verification(self):
  rows=[{'bet365_event_id':'abc123','event_match_method':'exact','bet365_odds':2.1,'bet365_verified':True}]
  self.assertEqual(exact_event_identity(rows),{'bet365_event_id':'abc123','event_match_method':'exact'})
if __name__=='__main__':unittest.main()
