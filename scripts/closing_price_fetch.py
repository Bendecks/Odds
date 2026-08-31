import json, os, pathlib, re, unicodedata
from datetime import datetime, timezone
import requests

BASE='https://api.odds-api.io/v3'
KEY=os.getenv('ODDS_API_IO_KEY','')
QUEUE=pathlib.Path('output/closing_price_queue.json')
LEDGER=pathlib.Path('data/model_closing_prices.jsonl')
STATUS=pathlib.Path('output/closing_price_fetch_status.json')
MAX_CALLS=int(os.getenv('CLOSING_MAX_ODDS_CALLS','10'))

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',s)

def split_event(name):
    p=re.split(r'\s+vs?\.?\s+',str(name or ''),maxsplit=1,flags=re.I)
    return p if len(p)==2 else (None,None)

def field_for(row):
    home,away=split_event(row.get('event')); pick=norm(row.get('pick'))
    if not home:return None
    if pick==norm(home):return 'home'
    if pick==norm(away):return 'away'
    if pick in ('draw','uafgjort'):return 'draw'
    return None

def bet365_markets(data):
    books=(data or {}).get('bookmakers') or {}
    markets=books.get('Bet365') or books.get('bet365') or []
    return markets if isinstance(markets,list) else []

def h2h_price(data,field):
    if field not in ('home','away','draw'):return None,None
    for m in bet365_markets(data):
        if str(m.get('name','')).lower() not in ('ml','moneyline','h2h','1x2'):continue
        odds=m.get('odds') or []
        if not odds or not isinstance(odds[0],dict):continue
        try:price=float(odds[0].get(field))
        except Exception:continue
        if price>1:return price,m.get('updatedAt')
    return None,None

def main():
    now=datetime.now(timezone.utc)
    try:q=json.loads(QUEUE.read_text())
    except Exception:q={}
    due=q.get('due') or []
    existing=[]; captured=set()
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:
                x=json.loads(line);existing.append(x)
                if x.get('signal_key') and x.get('closing_odds'):captured.add(str(x['signal_key']))
            except Exception:pass
    eligible=[]; skipped=[]
    for row in due:
        key=str(row.get('signal_key') or '')
        if not key or key in captured:continue
        if row.get('event_match_method')!='exact' or not row.get('bet365_event_id'):
            skipped.append({'signal_key':key,'reason':'missing_exact_provider_identity'});continue
        field=field_for(row)
        if not field:skipped.append({'signal_key':key,'reason':'unsupported_pick_identity'});continue
        eligible.append((row,field))
    attempts=0; successes=0; errors=[]; records=[]
    if eligible and not KEY:errors.append({'reason':'missing_ODDS_API_IO_KEY'})
    if KEY:
        for row,field in eligible[:MAX_CALLS]:
            eid=str(row['bet365_event_id']); attempts+=1
            try:
                r=requests.get(BASE+'/odds',params={'apiKey':KEY,'eventId':eid,'bookmakers':'Bet365'},timeout=30);r.raise_for_status();data=r.json();successes+=1
                price,provider_ts=h2h_price(data,field)
                if price is None:errors.append({'signal_key':row['signal_key'],'event_id':eid,'reason':'h2h_price_missing'});continue
                records.append({'signal_key':row['signal_key'],'event':row.get('event'),'market':row.get('market'),'pick':row.get('pick'),'taken_odds':row.get('taken_odds'),'closing_odds':price,'commence_time':row.get('commence_time'),'model_version':row.get('model_version'),'bet365_event_id':eid,'event_match_method':'exact','provider_timestamp':provider_ts,'captured_at':now.isoformat(),'source':'odds-api.io','bookmaker':'Bet365'})
            except requests.RequestException as exc:errors.append({'signal_key':row['signal_key'],'event_id':eid,'reason':type(exc).__name__})
    if records:
        LEDGER.parent.mkdir(exist_ok=True)
        with LEDGER.open('a') as f:
            for x in records:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'generated_at':now.isoformat(),'due_rows':len(due),'eligible_exact_rows':len(eligible),'provider_call_attempts':attempts,'provider_call_successes':successes,'odds_calls':attempts,'captured':len(records),'skipped':skipped[:50],'errors':errors[:50],'max_odds_calls':MAX_CALLS}
    STATUS.parent.mkdir(exist_ok=True);STATUS.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('skipped','errors')},ensure_ascii=False))

if __name__=='__main__':main()
