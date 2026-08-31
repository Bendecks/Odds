import json, pathlib, re, unicodedata
from datetime import datetime, timezone

CAND=pathlib.Path('data/value_candidates.json')
OBS=pathlib.Path('data/bet365_observations.jsonl')

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',s)

def event_key(text):
    parts=re.split(r'\s+vs?\.?\s+',str(text or ''),maxsplit=1,flags=re.I)
    return (norm(parts[0]),norm(parts[1])) if len(parts)==2 else None

def main():
    candidates=json.loads(CAND.read_text()) if CAND.exists() else []
    observations=[]
    if OBS.exists():
        for line in OBS.read_text().splitlines():
            try: observations.append(json.loads(line))
            except Exception: pass
    dc={}
    for o in observations:
        if str(o.get('market') or '').lower()!='double chance':continue
        key=event_key(o.get('event')); selection=str(o.get('selection') or '').upper()
        if key and selection in ('1X','12','X2'):
            dc[(key,selection)]=o
    matched=0
    for c in candidates:
        if str(c.get('market') or '').lower()!='double_chance':continue
        o=dc.get((event_key(c.get('event')),str(c.get('pick') or '').upper()))
        if not o:continue
        try: odds=float(o.get('odds',0))
        except Exception:continue
        if odds<=1:continue
        c.update({'bet365_odds':odds,'bet365_timestamp':o.get('timestamp') or datetime.now(timezone.utc).isoformat(),'bet365_verified':True,'bet365_source':'odds-api.io-derived-join','bet365_event_id':o.get('event_id'),'bet365_market':'Double Chance','event_match_method':'exact'})
        matched+=1
    CAND.write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'derived_double_chance_candidates':sum(1 for c in candidates if c.get('market')=='double_chance'),'derived_double_chance_bet365_matches':matched}))

if __name__=='__main__':main()
