import importlib.util,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('operational_status',ROOT/'scripts'/'operational_status.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class OperationalStatusTests(unittest.TestCase):
 def test_reports_exact_bet365_bottleneck_and_provider_health(self):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td);c=td/'candidates.json';d=td/'decision.json';b=td/'bet365.json';r=td/'ref.json';mc=td/'market.json';runs=td/'runs.jsonl';out=td/'out.json'
   c.write_text(json.dumps([{'event':'A vs B','fair_probability':.55,'books':3},{'event':'C vs D','fair_probability':.6,'books':3}]))
   d.write_text(json.dumps({'decision':'NO BET','mode':'PAPER','reason':'x'}))
   b.write_text(json.dumps({'provider_unavailable':False,'bet365_events_available':500,'events_queried':80,'provider_call_attempts':9,'odds_multi_calls':8,'fallback_odds_calls':1,'unique_markets':22,'raw_market_observations':1000}))
   r.write_text(json.dumps({'reference_events':2}))
   mc.write_text(json.dumps({}))
   runs.write_text(json.dumps({'decision':'NO BET'})+'\n')
   old=(m.CANDIDATES,m.DECISION,m.BET365,m.REFERENCE_DIAG,m.MARKET_COVERAGE,m.DECISION_RUNS,m.OUT);m.CANDIDATES,m.DECISION,m.BET365,m.REFERENCE_DIAG,m.MARKET_COVERAGE,m.DECISION_RUNS,m.OUT=c,d,b,r,mc,runs,out
   try:
    m.main();data=json.loads(out.read_text());self.assertEqual(data['funnel']['candidate_rows'],2);self.assertEqual(data['funnel']['exact_bet365_rows'],0);self.assertIn('Bet365',data['bottleneck']);self.assertIs(data['provider']['available'],True);self.assertEqual(data['provider']['odds_multi_calls'],8)
   finally:m.CANDIDATES,m.DECISION,m.BET365,m.REFERENCE_DIAG,m.MARKET_COVERAGE,m.DECISION_RUNS,m.OUT=old
if __name__=='__main__':unittest.main()
