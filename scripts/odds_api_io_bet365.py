import json, os, pathlib, re, unicodedata
from datetime import datetime, timezone, timedelta
import requests

BASE='https://api.odds-api.io/v3'
KEY=os.getenv('ODDS_API_IO_KEY','')
CAND=pathlib.Path('data/value_candidates.json')
OBS=pathlib.Path('data/bet365_observations.json')
STATUS=pathlib.Path('output/bet365_join_status.json')
MAX_HOURS=int(os.getenv('MAX_HOURS','72'))
MAX_ODDS_CALLS=int(os.getenv('BET365_MAX_ODDS_CALLS','80'))

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',s)

def get(path,params):
    r=requests.get(BASE+path,params={**params,'apiKey':KEY},timeout=30)
    r.raise_for_status(); return r.json()

def event_key(home,away): return norm(home),norm(away)

def parse_start(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None

def bet365_markets(data):
    books=(data or {}).get('bookmakers') or {}
    markets=books.get('Bet365') or books.get('bet365') or []
    return markets if isinstance(markets,list) else []

def market_rows(event,markets,now):
    rows=[]
    for m in markets:
        name=str(m.get('name') or m.get('key') or 'unknown')
        updated=m.get('updatedAt') or now.isoformat()
        odds=m.get('odds') or []
        for line in odds:
            if not isinstance(line,dict):continue
            # Preserve every numeric selection/line rather than deciding value here.
            for field,value in line.items():
                if field in ('id','name','label','handicap','hdp','point','line','total'):continue
                try:price=float(value)
                except Exception:continue
                if price<=1:continue
                rows.append({'event_id':event.get('id'),'event':f"{event.get('home')} vs {event.get('away')}",'home':event.get('home'),'away':event.get('away'),'sport':event.get('sport'),'league':event.get('league'),'commence_time':event.get('date') or event.get('startTime') or event.get('commence_time'),'market':name,'selection':field,'odds':price,'line':line.get('handicap',line.get('hdp',line.get('point',line.get('line',line.get('total'))))),'timestamp':updated,'bookmaker':'Bet365','source':'odds-api.io'})
    return rows

def main():
    if not KEY: raise SystemExit('Missing ODDS_API_IO_KEY')
    refs=json.loads(CAND.read_text()) if CAND.exists() else []
    now=datetime.now(timezone.utc); cutoff=now+timedelta(hours=MAX_HOURS)
    events=get('/events',{'sport':'football','bookmaker':'Bet365','status':'pending','limit':'500'})
    if isinstance(events,dict): events=events.get('data') or events.get('events') or []
    idx={event_key(e.get('home'),e.get('away')):e for e in events if e.get('id')}

    # Prioritize events that overlap the reference model, then fill remaining budget with
    # other imminent Bet365 events. This broadens discovery without pretending every event is value.
    ref_keys=[]
    for r in refs:
        parts=re.split(r'\s+vs?\.?\s+',str(r.get('event','')),maxsplit=1,flags=re.I)
        if len(parts)==2: ref_keys.append(event_key(parts[0],parts[1]))
    prioritized=[]; seen=set()
    for k in ref_keys:
        e=idx.get(k)
        if e and str(e.get('id')) not in seen: prioritized.append(e); seen.add(str(e.get('id')))
    for e in events:
        eid=str(e.get('id'))
        if not eid or eid in seen:continue
        start=parse_start(e.get('date') or e.get('startTime') or e.get('commence_time'))
        if start and now < start <= cutoff: prioritized.append(e); seen.add(eid)
    # If provider timestamps cannot be parsed, still keep reference-overlap events first.
    prioritized=prioritized[:MAX_ODDS_CALLS]

    cache={}; observations=[]; errors=[]; odds_calls=0
    for e in prioritized:
        eid=str(e['id'])
        try:
            cache[eid]=get('/odds',{'eventId':eid,'bookmakers':'Bet365'}); odds_calls+=1
            observations.extend(market_rows(e,bet365_markets(cache[eid]),now))
        except requests.HTTPError as exc:
            errors.append({'event_id':eid,'status':exc.response.status_code if exc.response is not None else None})
            cache[eid]={}

    # Join H2H/1X2 prices to the reference candidates, but do not discard unmatched observations.
    matched=0
    for r in refs:
        parts=re.split(r'\s+vs?\.?\s+',str(r.get('event','')),maxsplit=1,flags=re.I)
        if len(parts)!=2:continue
        e=idx.get(event_key(parts[0],parts[1]))
        if not e:continue
        markets=bet365_markets(cache.get(str(e['id']),{}))
        for m in markets:
            if str(m.get('name','')).lower() not in ('ml','moneyline','h2h','1x2'):continue
            odds=m.get('odds') or []
            if not odds or not isinstance(odds[0],dict):continue
            line=odds[0]; pick=norm(r.get('pick')); home=norm(e.get('home')); away=norm(e.get('away'))
            field='home' if pick==home else 'away' if pick==away else 'draw' if pick in ('draw','uafgjort') else None
            if not field or line.get(field) is None:continue
            try:price=float(line[field])
            except Exception:continue
            r.update({'bet365_odds':price,'bet365_timestamp':m.get('updatedAt') or now.isoformat(),'bet365_verified':True,'bet365_source':'odds-api.io','bet365_event_id':e.get('id')}); matched+=1; break

    CAND.write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n')
    OBS.parent.mkdir(exist_ok=True); OBS.write_text(json.dumps(observations,ensure_ascii=False,indent=2)+'\n')
    STATUS.parent.mkdir(exist_ok=True)
    STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'source':'odds-api.io','bet365_events_available':len(events),'events_queried':len(prioritized),'odds_calls':odds_calls,'raw_market_observations':len(observations),'matched_reference_candidates':matched,'max_odds_calls':MAX_ODDS_CALLS,'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print(f'Bet365 universe: available={len(events)} queried={len(prioritized)} observations={len(observations)} reference_matches={matched} errors={len(errors)}')
if __name__=='__main__': main()
