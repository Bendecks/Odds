import json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import derived_market_join as j

class TeamTotalJoinTests(unittest.TestCase):
 def run_join(self,candidates,observations):
  with tempfile.TemporaryDirectory() as d:
   cand=pathlib.Path(d)/'candidates.json';obs=pathlib.Path(d)/'obs.jsonl'
   cand.write_text(json.dumps(candidates));obs.write_text('\n'.join(json.dumps(x) for x in observations)+'\n')
   with patch.object(j,'CAND',cand),patch.object(j,'OBS',obs):j.main()
   return json.loads(cand.read_text())
 def base(self,line=1.5):
  return [
   {'event':'A vs B','event_id':'ref1','market':'h2h','pick':'A','fair_probability':.5,'event_match_method':'exact','bet365_event_id':'bet1','bet365_verified':True},
   {'event':'A vs B','event_id':'ref1','market':'team_total_goals_home','pick':'over','line':line,'fair_probability':.6,'bet365_verified':False},
  ]
 def test_matches_exact_provider_event_selection_and_line(self):
  out=self.run_join(self.base(),[{'event_id':'bet1','market':'Team Total Goals Home','selection':'over','line':1.5,'odds':1.91,'timestamp':'2026-09-01T05:00:00+00:00'}])
  row=out[1];self.assertTrue(row['bet365_verified']);self.assertEqual(row['bet365_odds'],1.91);self.assertEqual(row['event_match_method'],'exact')
 def test_wrong_line_does_not_match(self):
  out=self.run_join(self.base(),[{'event_id':'bet1','market':'Team Total Goals Home','selection':'over','line':2.5,'odds':2.1}])
  self.assertFalse(out[1]['bet365_verified'])
 def test_wrong_selection_does_not_match(self):
  out=self.run_join(self.base(),[{'event_id':'bet1','market':'Team Total Goals Home','selection':'under','line':1.5,'odds':1.9}])
  self.assertFalse(out[1]['bet365_verified'])
 def test_non_half_line_fails_closed(self):
  out=self.run_join(self.base(2.0),[{'event_id':'bet1','market':'Team Total Goals Home','selection':'over','line':2.0,'odds':1.9}])
  self.assertFalse(out[1]['bet365_verified'])
 def test_no_exact_sibling_identity_means_no_join(self):
  rows=self.base();rows[0]['event_match_method']='resolver';out=self.run_join(rows,[{'event_id':'bet1','market':'Team Total Goals Home','selection':'over','line':1.5,'odds':1.9}])
  self.assertFalse(out[1]['bet365_verified'])

if __name__=='__main__':unittest.main()
