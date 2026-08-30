import json, os, pathlib, re, unicodedata
from datetime import datetime, timezone, timedelta
import requests

BASE='https://api.odds-api.io/v3'
KEY=os.getenv('ODDS_API_IO_KEY','')
CAND=pathlib.Path('data/value_candidates.json')
STATUS=pathlib.Path('output/bet365_join_status.json')
MAX_HOURS=int(os.getenv('MAX_HOURS','72'))

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',s)

def get(path,params):
    r=requests.get(BASE+path,params={**params,'apiKey':KEY},timeout=30)
    r.raise_for_status(); return r.json()

def event_key(home,away): return norm(home),norm(away)

def ml_market(data):
    books=(data or {}).get('bookmakers') or {}
    markets=books.get('Bet365') or books.get('bet365') or []
    for m in markets:
        if str(m.get('name','')).lower() in ('ml','moneyline','h2h','1x2'):
            odds=m.get('odds') or []
            if odds and isinstance(odds[0],dict): return odds[0],m.get('updatedAt')
    return None,None

def main():
    if not KEY: raise SystemExit('Missing ODDS_API_IO_KEY')
    refs=json.loads(CAND.read_text()) if CAND.exists() else []
    now=datetime.now(timezone.utc); cutoff=now+timedelta(hours=MAX_HOURS)
    # Only football is needed by the current reference model. Filtering by Bet365 avoids irrelevant events.
    events=get('/events',{'sport':'football','bookmaker':'Bet365','status':'pending','limit':'500'})
    if isinstance(events,dict): events=events.get('data') or events.get('events') or []
    idx={event_key(e.get('home'),e.get('away')):e for e in events if e.get('id')}
    matched=0; odds_calls=0; errors=[]
    cache={}
    for r in refs:
        try:
            start=datetime.fromisoformat(str(r.get('commence_time')).replace('Z','+00:00')).astimezone(timezone.utc)
        except Exception: continue
        if not now < start <= cutoff: continue
        parts=re.split(r'\s+vs?\.?\s+',str(r.get('event','')),maxsplit=1,flags=re.I)
        if len(parts)!=2: continue
        e=idx.get(event_key(parts[0],parts[1]))
        if not e: continue
        eid=str(e['id'])
        if eid not in cache:
            try: cache[eid]=get('/odds',{'eventId':eid,'bookmakers':'Bet365'}); odds_calls+=1
            except requests.HTTPError as exc:
                errors.append({'event_id':eid,'status':exc.response.status_code if exc.response is not None else None}); cache[eid]={}
        ml,updated=ml_market(cache[eid])
        if not ml: continue
        home=norm(e.get('home')); away=norm(e.get('away')); pick=norm(r.get('pick'))
        field='home' if pick==home else 'away' if pick==away else 'draw' if pick in ('draw','uafgjort') else None
        if not field or ml.get(field) is None: continue
        try: price=float(ml[field])
        except Exception: continue
        stamp=updated or now.isoformat()
        r.update({'bet365_odds':price,'bet365_timestamp':stamp,'bet365_verified':True,'bet365_source':'odds-api.io','bet365_event_id':e.get('id')}); matched+=1
    CAND.write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n')
    STATUS.parent.mkdir(exist_ok=True)
    STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'source':'odds-api.io','bet365_events':len(events),'odds_calls':odds_calls,'matched_candidates':matched,'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print(f'Bet365 via odds-api.io: events={len(events)} odds_calls={odds_calls} matched={matched} errors={len(errors)}')
if __name__=='__main__': main()
