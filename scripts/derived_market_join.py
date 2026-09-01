import json, pathlib
from datetime import datetime, timezone
CAND=pathlib.Path('data/value_candidates.json');OBS=pathlib.Path('data/bet365_observations.jsonl')
MARKET_ALIASES={
 'double_chance':('double chance',),
 'draw_no_bet':('draw no bet',),
 'btts':('both teams to score','teams to score'),
 'odd_even':('odd/even',),
 'clean_sheet_home':('clean sheet home',),
 'clean_sheet_away':('clean sheet away',),
 'team_total_goals_home':('team total goals home',),
 'team_total_goals_away':('team total goals away',),
}
LINE_AWARE=('team_total_goals_home','team_total_goals_away')
# Exact-goal provider observations currently expose selection="odds" without the
# goal bucket in compact diagnostics. They deliberately remain unjoinable until
# the provider payload exposes an unambiguous bucket/line identity.
MATCHABLE=tuple(MARKET_ALIASES)
def norm_line(value):
 try:return round(float(value),3)
 except Exception:return None
def main():
 candidates=json.loads(CAND.read_text()) if CAND.exists() else []; observations=[]
 if OBS.exists():
  for line in OBS.read_text().splitlines():
   try:observations.append(json.loads(line))
   except Exception:pass
 # Reuse provider IDs already proven exact by the direct reference join. Never infer exact identity from names alone.
 exact_ids={}
 for c in candidates:
  if c.get('event_match_method')=='exact' and c.get('bet365_event_id') and c.get('event_id'):exact_ids[str(c['event_id'])]=str(c['bet365_event_id'])
 index={};line_index={}
 for o in observations:
  eid=str(o.get('event_id') or '');market=str(o.get('market') or '').lower();selection=str(o.get('selection') or '').lower()
  if not eid:continue
  index[(eid,market,selection)]=o
  line=norm_line(o.get('line'))
  if line is not None:line_index[(eid,market,selection,line)]=o
 matched={m:0 for m in MATCHABLE}
 for c in candidates:
  market=str(c.get('market') or '').lower()
  if market not in matched:continue
  eid=exact_ids.get(str(c.get('event_id') or ''))
  if not eid:continue
  if market in ('double_chance','btts','odd_even','clean_sheet_home','clean_sheet_away',*LINE_AWARE):wanted_selection=str(c.get('pick') or '').lower()
  else:
   event=str(c.get('event') or '')
   if ' vs ' not in event:continue
   home,away=event.split(' vs ',1);pick=str(c.get('pick') or '')
   if pick==home:wanted_selection='home'
   elif pick==away:wanted_selection='away'
   else:continue
  if market in LINE_AWARE:
   wanted_line=norm_line(c.get('line'))
   if wanted_line is None or abs((wanted_line%1)-0.5)>1e-9:continue
   o=next((line_index.get((eid,wanted_market,wanted_selection,wanted_line)) for wanted_market in MARKET_ALIASES[market] if line_index.get((eid,wanted_market,wanted_selection,wanted_line))),None)
  else:o=next((index.get((eid,wanted_market,wanted_selection)) for wanted_market in MARKET_ALIASES[market] if index.get((eid,wanted_market,wanted_selection))),None)
  if not o:continue
  try:odds=float(o.get('odds',0))
  except Exception:continue
  if odds<=1:continue
  c.update({'bet365_odds':odds,'bet365_timestamp':o.get('timestamp') or datetime.now(timezone.utc).isoformat(),'bet365_verified':True,'bet365_source':'odds-api.io-derived-join','bet365_event_id':eid,'bet365_market':o.get('market'),'event_match_method':'exact'});matched[market]+=1
 CAND.write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'derived_candidates':{m:sum(c.get('market')==m for c in candidates) for m in MATCHABLE},'derived_bet365_matches':matched,'exact_goal_markets_deferred':['exact_total_goals','home_exact_goals','away_exact_goals']},ensure_ascii=False))
if __name__=='__main__':main()
