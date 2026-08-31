import json, os, pathlib, statistics
from datetime import datetime, timezone, timedelta
import requests

BASE='https://api.the-odds-api.com'
KEY=os.getenv('THE_ODDS_API_KEY') or os.getenv('ODDS_API_KEY','')
DEFAULT_SPORTS='soccer_denmark_superliga,soccer_epl,soccer_spain_la_liga,soccer_germany_bundesliga,soccer_italy_serie_a,soccer_france_ligue_one,soccer_netherlands_eredivisie,soccer_uefa_champs_league'
CORE_SPORTS=[x for x in DEFAULT_SPORTS.split(',') if x]
SPORTS_OVERRIDE=os.getenv('THE_ODDS_SPORTS','').strip()
MAX_SPORTS=int(os.getenv('THE_ODDS_MAX_SPORTS','24'))
SPORTS_PER_RUN=max(1,int(os.getenv('THE_ODDS_SPORTS_PER_RUN','8')))
ROTATION_STATE=pathlib.Path('data/reference_sport_rotation.json')
BOOKMAKERS=[x.strip() for x in os.getenv('THE_ODDS_BOOKMAKERS','pinnacle,betfair_ex_eu,betsson,nordicbet,williamhill').split(',') if x.strip()]
MAX_HOURS=int(os.getenv('MAX_HOURS','72'))
OUT=pathlib.Path('data/value_candidates.json')
STATUS=pathlib.Path('output/the_odds_feed_status.json')

def api_time(dt):return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def get(path,params):
    r=requests.get(BASE+path,params={**params,'apiKey':KEY},timeout=30)
    meta={'remaining':r.headers.get('x-requests-remaining'),'used':r.headers.get('x-requests-used'),'last':r.headers.get('x-requests-last')}
    r.raise_for_status(); return r.json(),meta

def active_sports():
    if SPORTS_OVERRIDE:return [x.strip() for x in SPORTS_OVERRIDE.split(',') if x.strip()], 'override'
    try:
        data,_=get('/v4/sports',{})
        soccer=sorted(set(str(x.get('key')) for x in data if x.get('active') and str(x.get('key','')).startswith('soccer_') and not x.get('has_outrights')))
        return soccer, 'active-soccer-discovery'
    except Exception:return CORE_SPORTS[:MAX_SPORTS], 'fallback-defaults'

def rotation_cursor():
    try:return max(0,int(json.loads(ROTATION_STATE.read_text()).get('cursor',0)))
    except Exception:return 0

def select_sports(pool):
    if SPORTS_OVERRIDE:return pool[:min(len(pool),SPORTS_PER_RUN)],0
    budget=min(len(pool),SPORTS_PER_RUN)
    if not budget:return [],0
    core=[s for s in CORE_SPORTS if s in pool]
    # Keep a small stable core each run. Every other active competition—including
    # unselected defaults—belongs to the rotating pool, so nothing is permanently
    # excluded by ordering or by membership in DEFAULT_SPORTS.
    core_slots=min(len(core),budget if len(pool)<=budget else max(1,budget//2))
    stable=core[:core_slots]
    rotating=[s for s in pool if s not in stable]
    slots=budget-len(stable); cursor=rotation_cursor()
    if rotating and slots:
        selected=stable+[rotating[(cursor+i)%len(rotating)] for i in range(slots)]
        next_cursor=(cursor+slots)%len(rotating)
    else:selected=stable;next_cursor=cursor
    if len(selected)<budget:selected += [s for s in pool if s not in selected][:budget-len(selected)]
    return selected,next_cursor

def discover_sports():
    pool,source=active_sports(); selected,next_cursor=select_sports(pool)
    return selected,source,pool,next_cursor

def novig_fair(outcomes):
    valid=[o for o in outcomes if float(o.get('price',0) or 0)>1]; inv=[1/float(o['price']) for o in valid]; total=sum(inv)
    if len(inv)<2 or total<=0:return {}
    return {str(o['name']):(1/float(o['price']))/total for o in valid}
def quality(n):return 'strong' if n>=4 else 'good' if n>=3 else 'limited' if n>=2 else 'weak'

def main():
    if not KEY:raise SystemExit('Missing THE_ODDS_API_KEY/ODDS_API_KEY')
    sports,source,pool,next_cursor=discover_sports(); now=datetime.now(timezone.utc);end=now+timedelta(hours=MAX_HOURS);candidates=[];last_meta={};events_seen=0;errors=[]
    params={'bookmakers':','.join(BOOKMAKERS),'markets':'h2h','oddsFormat':'decimal','dateFormat':'iso','commenceTimeFrom':api_time(now),'commenceTimeTo':api_time(end)}
    for sport in sports:
        try:data,last_meta=get(f'/v4/sports/{sport}/odds',params)
        except requests.HTTPError as e:
            status=e.response.status_code if e.response is not None else None;body=(e.response.text[:500] if e.response is not None else str(e));errors.append({'sport':sport,'status':status,'error':body});continue
        events_seen+=len(data)
        for event in data:
            consensus={};offered={};books_by_pick={}
            for book in event.get('bookmakers',[]):
                bk=str(book.get('key') or book.get('title') or 'unknown')
                for market in book.get('markets',[]):
                    if market.get('key')!='h2h':continue
                    fair=novig_fair(market.get('outcomes',[]))
                    for outcome in market.get('outcomes',[]):
                        name=str(outcome.get('name'));price=float(outcome.get('price',0) or 0)
                        if price<=1:continue
                        if name in fair:consensus.setdefault(name,[]).append(fair[name])
                        offered.setdefault(name,[]).append(price);books_by_pick.setdefault(name,set()).add(bk)
            for pick,prices in offered.items():
                probs=consensus.get(pick,[]);fair=statistics.median(probs) if probs else None;n=len(books_by_pick.get(pick,set()))
                candidates.append({'event':f"{event.get('home_team')} vs {event.get('away_team')}",'event_id':event.get('id'),'sport':sport,'commence_time':event.get('commence_time'),'market':'h2h','pick':pick,'reference_odds':round(max(prices),3),'fair_probability':round(fair,6) if fair is not None else None,'books':n,'reference_books':sorted(books_by_pick.get(pick,set())),'reference_quality':quality(n),'discovery_eligible':True,'bookmaker':'REFERENCE_MARKET','bet365_verified':False,'model_version':'market-consensus-v3'})
    candidates.sort(key=lambda x:(x['books'],x['fair_probability'] or 0),reverse=True);quality_counts={};pick_counts={'draw':0,'team':0}
    for c in candidates:
        quality_counts[c['reference_quality']]=quality_counts.get(c['reference_quality'],0)+1;pick_counts['draw' if str(c['pick']).lower()=='draw' else 'team']+=1
    OUT.parent.mkdir(exist_ok=True);STATUS.parent.mkdir(exist_ok=True);ROTATION_STATE.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n')
    if not SPORTS_OVERRIDE:ROTATION_STATE.write_text(json.dumps({'cursor':next_cursor,'pool_size':len(pool),'last_sports':sports,'updated_at':now.isoformat()},ensure_ascii=False,indent=2)+'\n')
    STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'model_version':'market-consensus-v3','sports_source':source,'active_soccer_pool_size':len(pool),'sports_requested':sports,'sports_count':len(sports),'sports_per_run':SPORTS_PER_RUN,'max_sports':MAX_SPORTS,'rotation_next_cursor':next_cursor,'bookmakers':BOOKMAKERS,'events_seen':events_seen,'reference_observations':len(candidates),'quality_counts':quality_counts,'pick_type_counts':pick_counts,'discovery_policy':'full active-soccer pool with quota-aware rotation; preserve all offered h2h outcomes; confidence is metadata','quota':last_meta,'errors':errors},ensure_ascii=False,indent=2)+'\n')
    print(f'{len(candidates)} reference observations from {events_seen} events across {len(sports)}/{len(pool)} active sports ({source}); quota={last_meta}; errors={len(errors)}')
    if errors and events_seen==0:print(json.dumps(errors,ensure_ascii=False));raise SystemExit('No events returned; see feed status/errors above')
if __name__=='__main__':main()
