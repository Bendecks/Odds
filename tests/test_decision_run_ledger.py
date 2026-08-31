import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('decision_run_ledger',ROOT/'scripts'/'decision_run_ledger.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class DecisionRunLedgerTests(unittest.TestCase):
 def test_reads_current_bet365_status_field_names(self):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td);decision=td/'latest.json';candidates=td/'candidates.json';bet365=td/'bet365.json';reference=td/'reference.json';ledger=td/'runs.jsonl';status=td/'status.json'
   decision.write_text(json.dumps({'decision':'NO BET','reason':'x'}))
   candidates.write_text(json.dumps([{'fair_probability':.5,'bet365_verified':True}]))
   bet365.write_text(json.dumps({'events_queried':80,'matched_reference_candidates':3,'provider_unavailable':False}))
   reference.write_text(json.dumps({'events_seen':15,'reference_observations':45}))
   old=(m.DECISION,m.CANDIDATES,m.BET365,m.REFERENCE,m.LEDGER,m.STATUS);m.DECISION,m.CANDIDATES,m.BET365,m.REFERENCE,m.LEDGER,m.STATUS=decision,candidates,bet365,reference,ledger,status
   try:
    m.main();d=json.loads(status.read_text())['latest'];self.assertEqual(d['bet365_events_queried'],80);self.assertEqual(d['bet365_exact_matches'],3);self.assertIs(d['bet365_provider_available'],True)
   finally:m.DECISION,m.CANDIDATES,m.BET365,m.REFERENCE,m.LEDGER,m.STATUS=old
if __name__=='__main__':unittest.main()
