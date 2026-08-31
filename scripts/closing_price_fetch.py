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
    market=str(row.get('market') or 'h2h').lower();home,away=split_event(row.get('event')); pick=norm(row.get('pick'))
    if not home:return None
    if market in ('h2h','ml','1x2'):
        if pick==norm(home):return 'home'
        if pick==norm(away):return 'away'
        if pick in ('draw','uafgjort'):return 'draw'
    if market in ('totals','total'):
        return 'over' if pick=='over' else 'under' if pick=='under' else None
    if market in ('spreads','spread'):
        if pick==norm(home):return 'home'
        if pick==norm(away):return 'away'
    if market in ('btts','both teams to score','teams to score'):
        if pick in ('yes','ja'):return 'yes'
        if pick in ('no','nej'):return 'no'
    return None

def bet365_markets(data):
    books=(data or {}).get('bookmakers') or {}
    markets=books.get('Bet365') or books.get('bet365') or []
    return markets if isinstance(markets,list) else []

MARKET_ALIASES={
    'h2h':('ml','moneyline','h2h','1x2'),
    'ml':('ml','moneyline','h2h','1x2'),
    'totals':('totals','goals over/under','alternative total goals','alternative goal line'),
    'spreads':('spread','alternative asian handicap'),
    'btts':('both teams to score','teams to score'),
}

def market_matches(row,market):
    row_market=str(row.get('market') or 'h2h').lower()
    wanted=MARKET_ALIASES.get(row_market,(row_market,))
    return str(market or '').lower() in wanted

def line_matches(row,line_value):
    candidate_line=row.get('line')
    if candidate_line is None or candidate_line=='':return True
    if line_value is None or line_value=='':return False
    try:return abs(float(candidate_line)-float(line_value))<0.001
    except Exception:return str(candidate_line)==str(line_value)

def line_for_bet365(row,field):
    line=row.get('line')
    if str(row.get('market') or '').lower() in ('spreads','spread') and field=='away':
        try:return -float(line)
        except Exception:return line
    return line

def market_price(data,row,field):
    for m in bet365_markets(data):
        if not market_matches(row,m.get('name') or m.get('key')):continue
        odds=m.get('odds') or []
        for line in odds:
            if not isinstance(line,dict):continue
            line_value=line.get('handicap',line.get('hdp',line.get('point',line.get('line',line.get('total')))))
            probe={**row,'line':line_for_bet365(row,field)}
            if not line_matches(probe,line_value):continue
            try:price=float(line.get(field))
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
                price,provider_ts=market_price(data,row,field)
                if price is None:errors.append({'signal_key':row['signal_key'],'event_id':eid,'reason':'market_price_missing'});continue
                records.append({'signal_key':row['signal_key'],'event':row.get('event'),'market':row.get('market'),'line':row.get('line'),'pick':row.get('pick'),'taken_odds':row.get('taken_odds'),'closing_odds':price,'commence_time':row.get('commence_time'),'model_version':row.get('model_version'),'bet365_event_id':eid,'event_match_method':'exact','provider_timestamp':provider_ts,'captured_at':now.isoformat(),'source':'odds-api.io','bookmaker':'Bet365'})
            except requests.RequestException as exc:errors.append({'signal_key':row['signal_key'],'event_id':eid,'reason':type(exc).__name__})
    if records:
        LEDGER.parent.mkdir(exist_ok=True)
        with LEDGER.open('a') as f:
            for x in records:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'generated_at':now.isoformat(),'due_rows':len(due),'eligible_exact_rows':len(eligible),'provider_call_attempts':attempts,'provider_call_successes':successes,'odds_calls':attempts,'captured':len(records),'skipped':skipped[:50],'errors':errors[:50],'max_odds_calls':MAX_CALLS}
    STATUS.parent.mkdir(exist_ok=True);STATUS.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('skipped','errors')},ensure_ascii=False))

if __name__=='__main__':main()
