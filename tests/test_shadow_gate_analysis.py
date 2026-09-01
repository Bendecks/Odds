import pathlib,sys,unittest
from datetime import datetime,timezone,timedelta
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import shadow_gate_analysis as s

NOW=datetime(2026,9,1,12,tzinfo=timezone.utc)
def base(**kw):
 row={'event':'A vs B','event_id':'ref1','bet365_event_id':'b1','market':'h2h','pick':'A','fair_probability':.6,'bet365_odds':2.0,'books':3,'bet365_verified':True,'event_match_method':'exact','bet365_timestamp':(NOW-timedelta(minutes=5)).isoformat(),'commence_time':(NOW+timedelta(hours=1)).isoformat()}
 row.update(kw);return row
class ShadowGateTests(unittest.TestCase):
 def test_full_gate_includes_stake(self):
  r=s.evaluate(base(),NOW,.02,.025,3,20);self.assertTrue(r['gate_eligible']);self.assertTrue(r['stake_eligible']);self.assertTrue(r['paper_eligible'])
 def test_started_event_rejected(self):self.assertIsNone(s.evaluate(base(commence_time=(NOW-timedelta(seconds=1)).isoformat()),NOW,.02,.025,3,20))
 def test_stale_rejected(self):self.assertIsNone(s.evaluate(base(bet365_timestamp=(NOW-timedelta(minutes=21)).isoformat()),NOW,.02,.025,3,20))
 def test_paper_can_ignore_theoretical_minimum_stake(self):
  r=s.evaluate(base(fair_probability=.51,bet365_odds=2.1),NOW,0,0,3,20);self.assertTrue(r['gate_eligible']);self.assertFalse(r['stake_eligible']);self.assertTrue(r['paper_eligible'])
 def test_identity_reason_separates_event_price_and_market(self):
  self.assertEqual(s.identity_reason(base(bet365_event_id=None)),'event_identity')
  self.assertEqual(s.identity_reason(base(event_match_method='resolver')),'event_identity')
  self.assertEqual(s.identity_reason(base(bet365_odds=None)),'no_exact_bet365_price')
  self.assertEqual(s.identity_reason(base(bet365_verified=False)),'market_identity')
  self.assertIsNone(s.identity_reason(base()))
 def test_select_one_per_event(self):
  rows=[s.evaluate(base(market=f'm{i}',pick=f'p{i}'),NOW,0,0,3,20) for i in range(2)];self.assertEqual(len(s.select(rows)),1)
 def test_select_allows_distinct_events(self):
  a=s.evaluate(base(),NOW,0,0,3,20);b=s.evaluate(base(event='C vs D',event_id='ref2',bet365_event_id='b2'),NOW,0,0,3,20);self.assertEqual(len(s.select([a,b])),2)
if __name__=='__main__':unittest.main()
