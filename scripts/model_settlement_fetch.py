import json, os, pathlib, re, unicodedata
from datetime import datetime, timezone
import requests
from settlement_schema import settlement_key, valid_settlement

BASE='https://api.odds-api.io/v3'
KEY=os.getenv('ODDS_API_IO_KEY','')
QUEUE=pathlib.Path('output/model_settlement_queue.json')
SETTLED=pathlib.Path('data/model_settlements.jsonl')
CLOSES=pathlib.Path('data/model_closing_prices.jsonl')
STATUS=pathlib.Path('output/model_settlement_fetch_status.json')
MAX_CALLS=int(os.getenv('SETTLEMENT_MAX_EVENT_CALLS','20'))

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',s)
def split_event(name):
    p=re.split(r'\s+vs?\.?\s+',str(name or ''),maxsplit=1,flags=re.I);return p if len(p)==2 else (None,None)
def event_payload(data):
    if isinstance(data,dict):
        nested=data.get('data') or data.get('event')
        if isinstance(nested,dict):return nested
    return data if isinstance(data,dict) else {}
def numeric_pair(obj):
    if not isinstance(obj,dict):return None
    for hk,ak in (('home','away'),('home_score','away_score'),('homeScore','awayScore')):
        if obj.get(hk) is not None and obj.get(ak) is not None:
            try:return float(obj[hk]),float(obj[ak])
            except Exception:pass
    return None
def regulation_score_pair(event):
    scores=(event or {}).get('scores')
    if not isinstance(scores,dict):return None
    periods=scores.get('periods')
    if isinstance(periods,dict):
        for key in ('ft','full_time','fullTime','regulation'):
            pair=numeric_pair(periods.get(key))
            if pair:return pair
    return None
def score_pair(event):
    event=event or {}; regulation=regulation_score_pair(event)
    if regulation:return regulation
    scores=event.get('scores'); pair=numeric_pair(scores)
    if pair:return pair
    return numeric_pair(event)
def score_source(event):return 'regulation_ft' if regulation_score_pair(event) else 'top_level'
def has_extra_time_or_penalties(event):
    event=event or {}; scores=event.get('scores')
    containers=[event,scores if isinstance(scores,dict) else {}]
    periods=scores.get('periods') if isinstance(scores,dict) else None
    if isinstance(periods,dict):containers.append(periods)
    keys=('extra_time','extraTime','et','aet','penalties','penalty','shootout','penalty_shootout','penaltyShootout')
    for obj in containers:
        if not isinstance(obj,dict):continue
        for key in keys:
            value=obj.get(key)
            if value not in (None,False,'',0,{},[]):return True
    status=' '.join(str(event.get(k) or '') for k in ('status','statusText','stage','period')).lower()
    return any(token in status for token in ('extra time','after extra time','penalt','shootout'))
def settlement_score_pair(event):
    regulation=regulation_score_pair(event)
    if regulation:return regulation,'regulation_ft'
    if has_extra_time_or_penalties(event):return None,'ambiguous_knockout_score'
    pair=score_pair(event)
    return (pair,'top_level') if pair else (None,'missing_score')
def supported_market(row):
    return str(row.get('market') or '').lower() in ('h2h','ml','1x2','totals','total','spreads','spread','btts','both teams to score','teams to score')
def market_outcome(row,pair):
    h,a=pair;market=str(row.get('market') or '').lower();home,away=split_event(row.get('event'));pick=norm(row.get('pick'))
    if not home:return None
    if market in ('h2h','ml','1x2'):
        winner='draw' if h==a else 'home' if h>a else 'away';field='home' if pick==norm(home) else 'away' if pick==norm(away) else 'draw' if pick in ('draw','uafgjort') else None
        if not field:return None
        return 'win' if field==winner else 'loss'
    if market in ('totals','total'):
        try:line=float(row.get('line'))
        except Exception:return None
        goals=h+a
        if goals==line:return 'push'
        if pick=='over':return 'win' if goals>line else 'loss'
        if pick=='under':return 'win' if goals<line else 'loss'
        return None
    if market in ('btts','both teams to score','teams to score'):
        yes=h>0 and a>0
        if pick in ('yes','ja'):return 'win' if yes else 'loss'
        if pick in ('no','nej'):return 'loss' if yes else 'win'
        return None
    if market in ('spreads','spread'):
        try:line=float(row.get('line'))
        except Exception:return None
        side='home' if pick==norm(home) else 'away' if pick==norm(away) else None
        if not side:return None
        margin=(h+line)-a if side=='home' else (a+line)-h
        if margin==0:return 'push'
        return 'win' if margin>0 else 'loss'
    return None
def outcome(row,event):
    event=event_payload(event);status=str(event.get('status') or '').lower()
    if status in ('cancelled','canceled','void','postponed'):return 'void'
    if status not in ('settled','finished','completed','ended'):return None
    pair,_=settlement_score_pair(event)
    if not pair:return None
    return market_outcome(row,pair)
def read_jsonl(path):
    out=[]
    if not path.exists():return out
    for line in path.read_text().splitlines():
        try:out.append(json.loads(line))
        except Exception:pass
    return out
def existing_keys(rows):return {settlement_key(x) for x in rows if valid_settlement(x) and settlement_key(x)}

def main():
    now=datetime.now(timezone.utc);SETTLED.parent.mkdir(exist_ok=True);SETTLED.touch(exist_ok=True)
    try:q=json.loads(QUEUE.read_text())
    except Exception:q={}
    pending=q.get('pending') or [];existing=read_jsonl(SETTLED);settled_keys=existing_keys(existing);closes={str(x.get('signal_key')):x for x in read_jsonl(CLOSES) if x.get('signal_key') and x.get('closing_odds')};eligible=[];skipped=[]
    for row in pending:
        key=str(row.get('signal_key') or '')
        if not key or key in settled_keys:continue
        if not supported_market(row):skipped.append({'signal_key':key,'reason':'unsupported_market'});continue
        if row.get('event_match_method')!='exact' or not row.get('bet365_event_id'):skipped.append({'signal_key':key,'reason':'missing_exact_provider_identity'});continue
        eligible.append(row)
    records=[];errors=[];attempts=0;successes=0;added_keys=set()
    if eligible and not KEY:errors.append({'reason':'missing_ODDS_API_IO_KEY'})
    if KEY:
        for row in eligible[:MAX_CALLS]:
            eid=str(row['bet365_event_id']);attempts+=1
            try:
                r=requests.get(BASE+'/events/'+eid,params={'apiKey':KEY},timeout=30);r.raise_for_status();event=event_payload(r.json());successes+=1;result=outcome(row,event)
                if result is None:
                    _,source=settlement_score_pair(event)
                    if source=='ambiguous_knockout_score':skipped.append({'signal_key':row['signal_key'],'reason':source})
                    continue
                key=str(row['signal_key'])
                if key in settled_keys or key in added_keys:continue
                close=closes.get(key,{});pair,source=settlement_score_pair(event);records.append({**row,'result':result,'closing_odds':close.get('closing_odds'),'settled_at':now.isoformat(),'provider_event_status':event.get('status'),'final_score':pair,'score_source':source,'source':'odds-api.io','bookmaker':'Bet365'});added_keys.add(key)
            except requests.RequestException as exc:errors.append({'signal_key':row['signal_key'],'event_id':eid,'reason':type(exc).__name__})
    if records:
        with SETTLED.open('a') as f:
            for x in records:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'generated_at':now.isoformat(),'pending_rows':len(pending),'eligible_exact_modelled':len(eligible),'provider_call_attempts':attempts,'provider_call_successes':successes,'event_calls':attempts,'settled_records_added':len(records),'skipped':skipped[:50],'errors':errors[:50],'max_event_calls':MAX_CALLS};STATUS.parent.mkdir(exist_ok=True);STATUS.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('skipped','errors')},ensure_ascii=False))
if __name__=='__main__':main()
