import importlib.util, json, os, pathlib, tempfile, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('derived_market_join',ROOT/'scripts/derived_market_join.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


def direct():
 return {'event':'Home FC vs Away FC','event_id':'ref1','market':'h2h','pick':'Home FC','event_match_method':'exact','bet365_event_id':'b365-1','bet365_verified':True}

def derived(market,pick):
 return {'event':'Home FC vs Away FC','event_id':'ref1','market':market,'pick':pick,'fair_probability':0.55,'bet365_verified':False}

def obs(market,selection,odds=2.0):
 return {'event_id':'b365-1','market':market,'selection':selection,'odds':odds,'timestamp':'2026-08-31T12:00:00+00:00'}


class DerivedMarketJoinTests(unittest.TestCase):
 def run_join(self,candidates,observations):
  with tempfile.TemporaryDirectory() as td:
   old=os.getcwd();os.chdir(td)
   try:
    pathlib.Path('data').mkdir()
    pathlib.Path('data/value_candidates.json').write_text(json.dumps(candidates))
    pathlib.Path('data/bet365_observations.jsonl').write_text('\n'.join(json.dumps(x) for x in observations)+'\n')
    old_cand,old_obs=M.CAND,M.OBS
    M.CAND=pathlib.Path('data/value_candidates.json');M.OBS=pathlib.Path('data/bet365_observations.jsonl')
    try:M.main()
    finally:M.CAND,M.OBS=old_cand,old_obs
    return json.loads(pathlib.Path('data/value_candidates.json').read_text())
   finally:os.chdir(old)

 def test_btts_joins_only_through_exact_sibling_provider_id(self):
  out=self.run_join([direct(),derived('btts','yes')],[obs('Both Teams To Score','yes',1.91)])
  btts=next(x for x in out if x['market']=='btts')
  self.assertTrue(btts['bet365_verified']);self.assertEqual(btts['bet365_event_id'],'b365-1');self.assertEqual(btts['bet365_odds'],1.91)

 def test_btts_accepts_provider_teams_to_score_alias(self):
  out=self.run_join([direct(),derived('btts','no')],[obs('Teams to Score','no',2.07)])
  btts=next(x for x in out if x['market']=='btts')
  self.assertTrue(btts['bet365_verified']);self.assertEqual(btts['bet365_odds'],2.07);self.assertEqual(btts['bet365_market'],'Teams to Score')

 def test_btts_does_not_join_from_matching_names_without_exact_sibling(self):
  out=self.run_join([derived('btts','yes')],[obs('Both Teams To Score','yes',1.91)])
  self.assertFalse(out[0]['bet365_verified']);self.assertNotIn('bet365_odds',out[0])

 def test_unknown_dnb_pick_cannot_fall_through_to_away(self):
  out=self.run_join([direct(),derived('draw_no_bet','Unknown FC')],[obs('Draw No Bet','away',2.2)])
  dnb=next(x for x in out if x['market']=='draw_no_bet')
  self.assertFalse(dnb['bet365_verified']);self.assertNotIn('bet365_odds',dnb)

if __name__=='__main__':unittest.main()
