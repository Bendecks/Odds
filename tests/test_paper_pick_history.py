import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('paper_pick_history',ROOT/'scripts'/'paper_pick_history.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PaperHistoryTests(unittest.TestCase):
 def test_builds_open_and_settled_history(self):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td);s=td/'s';r=td/'r';c=td/'c';o=td/'o.json'
   s.write_text('\n'.join(json.dumps(x) for x in [{'signal_key':'a','decision':'PAPER PICK','event':'A vs B','pick':'A','odds':2,'stake':1,'edge':.1},{'signal_key':'b','decision':'NO BET'},{'signal_key':'c','decision':'PAPER PICK','event':'C vs D','pick':'D','odds':3,'stake':1,'edge':.2}])+'\n');r.write_text(json.dumps({'signal_key':'a','result':'win'})+'\n');c.write_text(json.dumps({'signal_key':'a','closing_odds':1.8,'clv_pct':11.11})+'\n')
   old=(m.SIGNALS,m.SETTLEMENTS,m.CLOSES,m.OUT);m.SIGNALS,m.SETTLEMENTS,m.CLOSES,m.OUT=s,r,c,o
   try:
    m.main();d=json.loads(o.read_text());self.assertEqual(d['paper_picks'],2);self.assertEqual(d['open_picks'],1);self.assertEqual(d['decisive_picks'],1);self.assertEqual(d['profit_dkk'],1);self.assertEqual(d['roi_pct'],100);self.assertEqual(d['rows'][1]['clv_pct'],11.11)
   finally:m.SIGNALS,m.SETTLEMENTS,m.CLOSES,m.OUT=old
if __name__=='__main__':unittest.main()
