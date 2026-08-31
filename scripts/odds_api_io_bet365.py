import json, os, pathlib, re, unicodedata, collections
from datetime import datetime, timezone, timedelta
import requests
from event_match_diagnostics import conservative_match

BASE='https://api.odds-api.io/v3'; KEY=os.getenv('ODDS_API_IO_KEY','')
CAND=pathlib.Path('data/value_candidates.json'); OBS=pathlib.Path('data/bet365_observations.jsonl'); SUMMARY=pathlib.Path('output/bet365_market_summary.json'); STATUS=pathlib.Path('output/bet365_join_status.json'); DIAG=pathlib.Path('output/reference_match_diagnostics.json')
MAX_HOURS=int(os.getenv('MAX_HOURS','72')); MAX_ODDS_CALLS=int(os.getenv('BET365_MAX_ODDS_CALLS','80')); MAX_RESOLVER_ROWS=int(os.getenv('BET365_MAX_RESOLVER_ROWS','50')); BATCH_SIZE=min(10,max(1,int(os.getenv('BET365_BATCH_SIZE','10'))))

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower(); return re.sub(r'[^a-z0-9]','',s)
def get(path,params):
    r=requests.get(BASE+path,params={**params,'apiKey':KEY},timeout=30); r.raise_for_status(); return r.json()
def event_key(home,away): return norm(home),norm(away)
def parse_start(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None
def ref_parts(r):
    parts=re.split(r'\s+vs?\.?\s+',str(r.get('event','')),maxsplit=1,flags=re.I); return parts if len(parts)==2 else (None,None)
def ref_start(r): return r.get('commence_time') or r.get('start_time') or r.get('event_start') or r.get('kickoff')
def clear_bet365(refs):
    for r in refs:
        for k in list(r):
            if k.startswith('bet365_') or k=='event_match_method':r.pop(k,None)
    return refs
def unique_reference_events(refs):
    unique={}
    for r in refs:
        home,away=ref_parts(r)
        if not home:continue
        start=parse_start(ref_start(r)); start_key=start.isoformat() if start else str(ref_start(r) or '')
        key=(*event_key(home,away),start_key)
        if key not in unique:unique[key]=(r,home,away)
    return unique
def resolver_diagnostics(refs,idx,events):
    rows=[]; accepted_ids=set(); counts=collections.Counter(); unique=unique_reference_events(refs)
    for _,(r,home,away) in unique.items():
        if event_key(home,away) in idx:continue
        start=ref_start(r); result={'accepted':False,'reason':'missing_reference_start'} if not start else conservative_match(home,away,start,events)
        counts[result.get('reason','unknown')]+=1
        if result.get('accepted') and result.get('best',{}).get('event_id') is not None:accepted_ids.add(str(result['best']['event_id']))
        if len(rows)<MAX_RESOLVER_ROWS:rows.append({'reference_event':r.get('event'),'reference_start':start,**result})
    return rows,accepted_ids,counts,len(unique)
def bet365_markets(data):
    books=(data or {}).get('bookmakers') or {}; markets=books.get('Bet365') or books.get('bet365') or []; return markets if isinstance(markets,list) else []
def market_rows(event,markets,now):
    rows=[]
    for m in markets:
        name=str(m.get('name') or m.get('key') or 'unknown'); updated=m.get('updatedAt') or now.isoformat()
        for line in m.get('odds') or []:
            if not isinstance(line,dict):continue
            line_value=line.get('handicap',line.get('hdp',line.get('point',line.get('line',line.get('total')))))
            for field,value in line.items():
                if field in ('id','name','label','handicap','hdp','point','line','total'):continue
                try:price=float(value)
                except Exception:continue
                if price<=1:continue
                rows.append({'event_id':event.get('id'),'event':f"{event.get('home')} vs {event.get('away')}",'home':event.get('home'),'away':event.get('away'),'sport':event.get('sport'),'league':event.get('league'),'commence_time':event.get('date') or event.get('startTime') or event.get('commence_time'),'market':name,'selection':field,'odds':price,'line':line_value,'timestamp':updated,'bookmaker':'Bet365','source':'odds-api.io'})
    return rows

def chunks(rows,size):
    for i in range(0,len(rows),size):yield rows[i:i+size]
def fetch_odds(prioritized,now):
    cache={};observations=[];errors=[];attempts=successes=batch_attempts=batch_successes=fallback_attempts=fallback_successes=0
    event_by_id={str(e['id']):e for e in prioritized}
    for group in chunks(prioritized,BATCH_SIZE):
        ids=[str(e['id']) for e in group];attempts+=1;batch_attempts+=1
        try:
            payload=get('/odds/multi',{'eventIds':','.join(ids),'bookmakers':'Bet365'});successes+=1;batch_successes+=1
            rows=payload if isinstance(payload,list) else payload.get('data') or payload.get('events') or [] if isinstance(payload,dict) else []
            returned=set()
            for data in rows:
                eid=str((data or {}).get('id') or (data or {}).get('eventId') or '')
                if eid not in event_by_id:continue
                returned.add(eid);cache[eid]=data;observations.extend(market_rows(event_by_id[eid],bet365_markets(data),now))
            missing=[eid for eid in ids if eid not in returned]
        except requests.RequestException as exc:
            errors.append({'event_ids':ids,'stage':'odds_multi','status':exc.response.status_code if isinstance(exc,requests.HTTPError) and exc.response is not None else None,'reason':type(exc).__name__});missing=ids
        for eid in missing:
            attempts+=1;fallback_attempts+=1
            try:
                data=get('/odds',{'eventId':eid,'bookmakers':'Bet365'});successes+=1;fallback_successes+=1;cache[eid]=data;observations.extend(market_rows(event_by_id[eid],bet365_markets(data),now))
            except requests.RequestException as exc:
                errors.append({'event_id':eid,'stage':'odds_fallback','status':exc.response.status_code if isinstance(exc,requests.HTTPError) and exc.response is not None else None,'reason':type(exc).__name__});cache[eid]={}
    return cache,observations,errors,attempts,successes,batch_attempts,batch_successes,fallback_attempts,fallback_successes

def unavailable(refs,now,exc):
    clear_bet365(refs); CAND.write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n')
    status=exc.response.status_code if isinstance(exc,requests.HTTPError) and exc.response is not None else None; error={'stage':'events','status':status,'reason':'rate_limited' if status==429 else type(exc).__name__}; ref_events=len(unique_reference_events(refs))
    OBS.parent.mkdir(exist_ok=True);OBS.write_text('');SUMMARY.parent.mkdir(exist_ok=True);SUMMARY.write_text(json.dumps({'generated_at':now.isoformat(),'events_queried':0,'observations':0,'unique_markets':0,'top_markets':[],'top_leagues':[],'selection_fields':[],'provider_unavailable':True},indent=2)+'\n')
    DIAG.write_text(json.dumps({'generated_at':now.isoformat(),'reference_rows':len(refs),'reference_events':ref_events,'exact_reference_events_in_bet365':0,'unmatched_reference_events':ref_events,'exact_reference_rows':0,'exact_rows_not_queried':0,'queried_reference_rows_without_h2h_price':0,'matched_prices':0,'bet365_events_available':0,'bet365_events_queried':0,'resolver_diagnostic_only':True,'resolver_accepted_events':0,'resolver_reason_counts':{},'resolver_matches':[],'resolver_rows_persisted':0,'resolver_rows_limit':MAX_RESOLVER_ROWS,'provider_unavailable':True},ensure_ascii=False,indent=2)+'\n')
    STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'source':'odds-api.io','provider_unavailable':True,'bet365_events_available':0,'events_queried':0,'provider_call_attempts':1,'provider_call_successes':0,'odds_calls':0,'raw_market_observations':0,'unique_markets':0,'matched_reference_candidates':0,'resolver_accepted_events_diagnostic_only':0,'max_odds_calls':MAX_ODDS_CALLS,'errors':[error]},ensure_ascii=False,indent=2)+'\n');print('Bet365 provider unavailable for this run: '+json.dumps(error))

def main():
    if not KEY: raise SystemExit('Missing ODDS_API_IO_KEY')
    refs=clear_bet365(json.loads(CAND.read_text()) if CAND.exists() else []); CAND.write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n'); now=datetime.now(timezone.utc); cutoff=now+timedelta(hours=MAX_HOURS)
    try:events=get('/events',{'sport':'football','bookmaker':'Bet365','status':'pending','limit':'500'})
    except requests.RequestException as exc:return unavailable(refs,now,exc)
    events=(events.get('data') or events.get('events') or []) if isinstance(events,dict) else events; idx={event_key(e.get('home'),e.get('away')):e for e in events if e.get('id')}; ref_keys=[]
    for r in refs:
        home,away=ref_parts(r)
        if home:ref_keys.append(event_key(home,away))
    unique_ref_keys=set(ref_keys); exact_ref_keys={k for k in unique_ref_keys if k in idx}; resolver_rows,resolver_event_ids,resolver_counts,resolver_unique_events=resolver_diagnostics(refs,idx,events)
    prioritized=[]; seen=set()
    for k in ref_keys:
        e=idx.get(k)
        if e and str(e.get('id')) not in seen:prioritized.append(e);seen.add(str(e.get('id')))
    for e in events:
        eid=str(e.get('id'))
        if eid in resolver_event_ids and eid not in seen:prioritized.append(e);seen.add(eid)
    for e in events:
        eid=str(e.get('id'))
        if not eid or eid in seen:continue
        start=parse_start(e.get('date') or e.get('startTime') or e.get('commence_time'))
        if start and now<start<=cutoff:prioritized.append(e);seen.add(eid)
    prioritized=prioritized[:MAX_ODDS_CALLS]; queried_ids={str(e.get('id')) for e in prioritized}
    cache,observations,errors,attempts,successes,batch_attempts,batch_successes,fallback_attempts,fallback_successes=fetch_odds(prioritized,now)
    matched=0; exact_rows=0; exact_but_not_queried=0; queried_without_h2h_price=0
    for r in refs:
        home_name,away_name=ref_parts(r)
        if not home_name:continue
        e=idx.get(event_key(home_name,away_name))
        if not e:continue
        exact_rows+=1
        if str(e.get('id')) not in queried_ids:exact_but_not_queried+=1;continue
        found=False
        for m in bet365_markets(cache.get(str(e['id']),{})):
            if str(m.get('name','')).lower() not in ('ml','moneyline','h2h','1x2'):continue
            odds=m.get('odds') or []
            if not odds or not isinstance(odds[0],dict):continue
            line=odds[0];pick=norm(r.get('pick'));home=norm(e.get('home'));away=norm(e.get('away'));field='home' if pick==home else 'away' if pick==away else 'draw' if pick in ('draw','uafgjort') else None
            if not field or line.get(field) is None:continue
            try:price=float(line[field])
            except Exception:continue
            r.update({'bet365_odds':price,'bet365_timestamp':m.get('updatedAt') or now.isoformat(),'bet365_verified':True,'bet365_source':'odds-api.io','bet365_event_id':e.get('id'),'event_match_method':'exact'});matched+=1;found=True;break
        if not found:queried_without_h2h_price+=1
    CAND.write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n');OBS.parent.mkdir(exist_ok=True);OBS.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in observations))
    markets=collections.Counter(x['market'] for x in observations); leagues=collections.Counter(str(x.get('league') or 'unknown') for x in observations); selections=collections.Counter(x['selection'] for x in observations)
    summary={'generated_at':now.isoformat(),'events_queried':len(prioritized),'observations':len(observations),'unique_markets':len(markets),'top_markets':markets.most_common(100),'top_leagues':leagues.most_common(50),'selection_fields':selections.most_common(50)}
    diagnostics={'generated_at':now.isoformat(),'reference_rows':len(refs),'reference_events':resolver_unique_events,'exact_reference_events_in_bet365':len(exact_ref_keys),'unmatched_reference_events':len(unique_ref_keys-exact_ref_keys),'exact_reference_rows':exact_rows,'exact_rows_not_queried':exact_but_not_queried,'queried_reference_rows_without_h2h_price':queried_without_h2h_price,'matched_prices':matched,'bet365_events_available':len(events),'bet365_events_queried':len(prioritized),'resolver_diagnostic_only':True,'resolver_accepted_events':len(resolver_event_ids),'resolver_reason_counts':dict(resolver_counts),'resolver_matches':resolver_rows,'resolver_rows_persisted':len(resolver_rows),'resolver_rows_limit':MAX_RESOLVER_ROWS}
    SUMMARY.parent.mkdir(exist_ok=True);SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');DIAG.write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2)+'\n');STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'source':'odds-api.io','provider_unavailable':False,'bet365_events_available':len(events),'events_queried':len(prioritized),'provider_call_attempts':attempts+1,'provider_call_successes':successes+1,'odds_calls':attempts,'batch_size':BATCH_SIZE,'batch_attempts':batch_attempts,'batch_successes':batch_successes,'fallback_attempts':fallback_attempts,'fallback_successes':fallback_successes,'raw_market_observations':len(observations),'unique_markets':len(markets),'matched_reference_candidates':matched,'resolver_accepted_events_diagnostic_only':len(resolver_event_ids),'max_odds_calls':MAX_ODDS_CALLS,'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print(f'Bet365 universe: available={len(events)} queried={len(prioritized)} calls={attempts} batch={batch_successes}/{batch_attempts} fallback={fallback_successes}/{fallback_attempts} observations={len(observations)} reference_matches={matched} errors={len(errors)}')
if __name__=='__main__':main()
