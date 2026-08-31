import json, os, pathlib, re, unicodedata
from datetime import datetime, timezone
import requests

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
    p=re.split(r'\s+vs?\.?\s+',str(name or ''),maxsplit=1,flags=re.I)
    return p if len(p)==2 else (None,None)

def outcome(row, event):
    status=str((event or {}).get('status') or '').lower()
    if status in ('cancelled','canceled','void','postponed'):return 'void'
    if status not in ('settled','finished','completed','ended'):return None
    scores=(event or {}).get('scores') or {}
    try:h=float(scores.get('home'));a=float(scores.get('away'))
    except Exception:return None
    home,away=split_event(row.get('event'));pick=norm(row.get('pick'))
    if not home:return None
    if h==a:winner='draw'
    elif h>a:winner='home'
    else:winner='away'
    field='home' if pick==norm(home) else 'away' if pick==norm(away) else 'draw' if pick in ('draw','uafgjort') else None
    if not field:return None
    return 'win' if field==winner else 'loss'

def read_jsonl(path):
    out=[]
    if not path.exists():return out
    for line in path.read_text().splitlines():
        try:out.append(json.loads(line))
        except Exception:pass
    return out

def main():
    now=datetime.now(timezone.utc)
    try:q=json.loads(QUEUE.read_text())
    except Exception:q={}
    pending=q.get('pending') or []
    existing=read_jsonl(SETTLED); settled_keys={str(x.get('signal_key')) for x in existing if x.get('signal_key')}
    closes={str(x.get('signal_key')):x for x in read_jsonl(CLOSES) if x.get('signal_key') and x.get('closing_odds')}
    eligible=[];skipped=[]
    for row in pending:
        key=str(row.get('signal_key') or '')
        if not key or key in settled_keys:continue
        if row.get('market') not in ('h2h','ML','1x2'):
            skipped.append({'signal_key':key,'reason':'unsupported_market'});continue
        if row.get('event_match_method')!='exact' or not row.get('bet365_event_id'):
            skipped.append({'signal_key':key,'reason':'missing_exact_provider_identity'});continue
        eligible.append(row)
    records=[];errors=[];attempts=0;successes=0
    if eligible and not KEY:errors.append({'reason':'missing_ODDS_API_IO_KEY'})
    if KEY:
        for row in eligible[:MAX_CALLS]:
            eid=str(row['bet365_event_id']); attempts+=1
            try:
                r=requests.get(BASE+'/events/'+eid,params={'apiKey':KEY},timeout=30);r.raise_for_status();event=r.json();successes+=1
                result=outcome(row,event)
                if result is None:continue
                close=closes.get(str(row['signal_key']),{})
                records.append({**row,'result':result,'closing_odds':close.get('closing_odds'),'settled_at':now.isoformat(),'provider_event_status':event.get('status'),'final_score':event.get('scores'),'source':'odds-api.io','bookmaker':'Bet365'})
            except requests.RequestException as exc:errors.append({'signal_key':row['signal_key'],'event_id':eid,'reason':type(exc).__name__})
    if records:
        SETTLED.parent.mkdir(exist_ok=True)
        with SETTLED.open('a') as f:
            for x in records:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'generated_at':now.isoformat(),'pending_rows':len(pending),'eligible_exact_h2h':len(eligible),'provider_call_attempts':attempts,'provider_call_successes':successes,'event_calls':attempts,'settled_records_added':len(records),'skipped':skipped[:50],'errors':errors[:50],'max_event_calls':MAX_CALLS}
    STATUS.parent.mkdir(exist_ok=True);STATUS.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('skipped','errors')},ensure_ascii=False))

if __name__=='__main__':main()
