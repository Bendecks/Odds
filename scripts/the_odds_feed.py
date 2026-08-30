import json, os, pathlib, statistics
from datetime import datetime, timezone, timedelta
import requests

BASE='https://api.the-odds-api.com'
KEY=os.getenv('THE_ODDS_API_KEY') or os.getenv('ODDS_API_KEY','')
SPORTS=[x.strip() for x in os.getenv('THE_ODDS_SPORTS','soccer_denmark_superliga,soccer_epl,soccer_spain_la_liga,soccer_germany_bundesliga,soccer_italy_serie_a,soccer_france_ligue_one,soccer_netherlands_eredivisie,soccer_uefa_champs_league').split(',') if x.strip()]
BOOKMAKERS=[x.strip() for x in os.getenv('THE_ODDS_BOOKMAKERS','pinnacle,betfair_ex_eu,betsson,nordicbet,williamhill').split(',') if x.strip()]
MAX_HOURS=int(os.getenv('MAX_HOURS','72'))
OUT=pathlib.Path('data/value_candidates.json')
STATUS=pathlib.Path('output/the_odds_feed_status.json')

def api_time(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def get(path,params):
    r=requests.get(BASE+path,params={**params,'apiKey':KEY},timeout=30)
    meta={'remaining':r.headers.get('x-requests-remaining'),'used':r.headers.get('x-requests-used'),'last':r.headers.get('x-requests-last')}
    r.raise_for_status(); return r.json(),meta

def novig_fair(outcomes):
    valid=[o for o in outcomes if float(o.get('price',0) or 0)>1]
    inv=[1/float(o['price']) for o in valid]; total=sum(inv)
    if len(inv)<2 or total<=0:return {}
    return {str(o['name']):(1/float(o['price']))/total for o in valid}

def quality(book_count):
    if book_count>=4:return 'strong'
    if book_count>=3:return 'good'
    if book_count>=2:return 'limited'
    return 'weak'

def main():
    if not KEY: raise SystemExit('Missing THE_ODDS_API_KEY/ODDS_API_KEY')
    now=datetime.now(timezone.utc); end=now+timedelta(hours=MAX_HOURS); candidates=[]; last_meta={}; events_seen=0; errors=[]
    params={'bookmakers':','.join(BOOKMAKERS),'markets':'h2h','oddsFormat':'decimal','dateFormat':'iso','commenceTimeFrom':api_time(now),'commenceTimeTo':api_time(end)}
    for sport in SPORTS:
        try:data,last_meta=get(f'/v4/sports/{sport}/odds',params)
        except requests.HTTPError as e:
            status=e.response.status_code if e.response is not None else None
            body=(e.response.text[:500] if e.response is not None else str(e))
            errors.append({'sport':sport,'status':status,'error':body}); continue
        events_seen+=len(data)
        for event in data:
            consensus={}; offered={}
            for book in event.get('bookmakers',[]):
                for market in book.get('markets',[]):
                    if market.get('key')!='h2h':continue
                    fair=novig_fair(market.get('outcomes',[]))
                    for outcome in market.get('outcomes',[]):
                        name=str(outcome.get('name')); price=float(outcome.get('price',0) or 0)
                        if price<=1:continue
                        if name in fair: consensus.setdefault(name,[]).append(fair[name])
                        offered.setdefault(name,[]).append(price)
            for pick,probs in consensus.items():
                if not probs:continue
                fair=statistics.median(probs); prices=offered.get(pick,[])
                if not prices:continue
                candidates.append({'event':f"{event.get('home_team')} vs {event.get('away_team')}",'event_id':event.get('id'),'sport':sport,'commence_time':event.get('commence_time'),'market':'h2h','pick':pick,'reference_odds':round(max(prices),3),'fair_probability':round(fair,6),'books':len(probs),'reference_quality':quality(len(probs)),'bookmaker':'REFERENCE_MARKET','bet365_verified':False,'model_version':'market-consensus-v2'})
    candidates.sort(key=lambda x:(x['books'],x['fair_probability']),reverse=True)
    quality_counts={}
    for c in candidates:quality_counts[c['reference_quality']]=quality_counts.get(c['reference_quality'],0)+1
    OUT.parent.mkdir(exist_ok=True); STATUS.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n')
    STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'sports_requested':SPORTS,'bookmakers':BOOKMAKERS,'events_seen':events_seen,'reference_observations':len(candidates),'quality_counts':quality_counts,'quota':last_meta,'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print(f'{len(candidates)} reference observations from {events_seen} events; quality={quality_counts}; quota={last_meta}; errors={len(errors)}')
    if errors and events_seen==0:
        print(json.dumps(errors,ensure_ascii=False)); raise SystemExit('No events returned; see feed status/errors above')
if __name__=='__main__':main()
