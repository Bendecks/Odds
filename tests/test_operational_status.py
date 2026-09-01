import importlib.util,json,pathlib,sys,tempfile,unittest
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('operational_status',ROOT/'scripts'/'operational_status.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class OperationalStatusTests(unittest.TestCase):
 def run_status(self,candidates):
  td=tempfile.TemporaryDirectory();p=pathlib.Path(td.name);c=p/'candidates.json';d=p/'decision.json';b=p/'bet365.json';r=p/'ref.json';mc=p/'market.json';runs=p/'runs.jsonl';out=p/'out.json'
  c.write_text(json.dumps(candidates));d.write_text(json.dumps({'decision':'NO BET','mode':'PAPER','reason':'x'}));b.write_text(json.dumps({'provider_unavailable':False,'bet365_events_available':500,'events_queried':80,'provider_call_attempts':9,'batch_attempts':8,'fallback_attempts':1,'unique_markets':22,'raw_market_observations':1000}));r.write_text(json.dumps({'reference_events':2}));mc.write_text('{}');runs.write_text(json.dumps({'decision':'NO BET'})+'\n')
  old=(m.CANDIDATES,m.DECISION,m.BET365,m.REFERENCE_DIAG,m.MARKET_COVERAGE,m.DECISION_RUNS,m.OUT);m.CANDIDATES,m.DECISION,m.BET365,m.REFERENCE_DIAG,m.MARKET_COVERAGE,m.DECISION_RUNS,m.OUT=c,d,b,r,mc,runs,out
  try:m.main();return json.loads(out.read_text())
  finally:m.CANDIDATES,m.DECISION,m.BET365,m.REFERENCE_DIAG,m.MARKET_COVERAGE,m.DECISION_RUNS,m.OUT=old;td.cleanup()
 def test_reports_exact_bet365_bottleneck_and_provider_health(self):
  data=self.run_status([{'event':'A vs B','fair_probability':.55,'books':3},{'event':'C vs D','fair_probability':.6,'books':3}]);self.assertEqual(data['funnel']['candidate_rows'],2);self.assertEqual(data['funnel']['exact_bet365_rows'],0);self.assertIn('Bet365',data['bottleneck']);self.assertIs(data['provider']['available'],True);self.assertEqual(data['provider']['odds_multi_calls'],8)
 def test_edge_and_ev_only_count_after_freshness_and_reference_gates(self):
  now=datetime.now(timezone.utc);fresh=now.isoformat();stale='2026-01-01T00:00:00+00:00';start='2099-01-01T00:00:00+00:00'
  base={'event':'A vs B','event_id':'1','commence_time':start,'market':'h2h','pick':'A','fair_probability':.60,'books':3,'bet365_verified':True,'bet365_event_id':'99','event_match_method':'exact','bet365_odds':2.0}
  data=self.run_status([{**base,'bet365_timestamp':stale},{**base,'event_id':'2','bet365_event_id':'100','bet365_timestamp':fresh,'books':2}]);self.assertEqual(data['funnel']['exact_bet365_rows'],2);self.assertEqual(data['funnel']['fresh_exact_bet365_rows'],1);self.assertEqual(data['funnel']['reference_depth_ready_rows'],0);self.assertEqual(data['funnel']['positive_edge_rows'],0);self.assertEqual(data['funnel']['ev_ready_rows'],0);self.assertIn('referencebøger',data['bottleneck'])
 def test_dnb_diagnostics_use_push_aware_edge_and_ev(self):
  c={'market':'draw_no_bet','fair_probability':.75,'win_probability':.45,'loss_probability':.15,'push_probability':.40,'bet365_odds':1.8};edge,ev=m.candidate_edge(c);self.assertAlmostEqual(edge,.75-(1/1.8));self.assertAlmostEqual(ev,.45*.8-.15)
if __name__=='__main__':unittest.main()
