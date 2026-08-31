import json, pathlib
from datetime import datetime, timezone
CAND=pathlib.Path('data/value_candidates.json');OBS=pathlib.Path('data/bet365_observations.jsonl')
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
 index={}
 for o in observations:
  eid=str(o.get('event_id') or '');market=str(o.get('market') or '').lower();selection=str(o.get('selection') or '').lower()
  if eid:index[(eid,market,selection)]=o
 matched={'double_chance':0,'draw_no_bet':0}
 for c in candidates:
  market=str(c.get('market') or '').lower()
  if market not in matched:continue
  eid=exact_ids.get(str(c.get('event_id') or ''))
  if not eid:continue
  if market=='double_chance':wanted_market='double chance';wanted_selection=str(c.get('pick') or '').lower()
  else:
   wanted_market='draw no bet';event=str(c.get('event') or '');home=event.split(' vs ')[0] if ' vs ' in event else '';wanted_selection='home' if str(c.get('pick'))==home else 'away'
  o=index.get((eid,wanted_market,wanted_selection))
  if not o:continue
  try:odds=float(o.get('odds',0))
  except Exception:continue
  if odds<=1:continue
  c.update({'bet365_odds':odds,'bet365_timestamp':o.get('timestamp') or datetime.now(timezone.utc).isoformat(),'bet365_verified':True,'bet365_source':'odds-api.io-derived-join','bet365_event_id':eid,'bet365_market':o.get('market'),'event_match_method':'exact'});matched[market]+=1
 CAND.write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'derived_double_chance_candidates':sum(c.get('market')=='double_chance' for c in candidates),'derived_double_chance_bet365_matches':matched['double_chance'],'derived_draw_no_bet_candidates':sum(c.get('market')=='draw_no_bet' for c in candidates),'derived_draw_no_bet_bet365_matches':matched['draw_no_bet']}))
if __name__=='__main__':main()
