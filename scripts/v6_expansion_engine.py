import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
CACHE=OUT/'odds_cache_raw.json'
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
ODDS_IO=os.getenv('ODDS_API_IO_KEY','')
MODEL=os.getenv('GEMINI_MODEL','gemini-2.5-flash')
MODE='V7_MULTI_SPORT_ENGINE_FIXED'
MAX_HOURS=int(os.getenv('MAX_HOURS','168'))
MAX_TOP_BETS=int(os.getenv('MAX_TOP_BETS','20'))
MIN_TOP_SCORE=float(os.getenv('MIN_TOP_SCORE','7.0'))
MAX_AUTO_ODDS=float(os.getenv('MAX_AUTO_ODDS','6.0'))
DISPLAY_TZ=os.getenv('DISPLAY_TZ','Europe/Copenhagen')
MARKETS=('h2h','spreads','totals')
SPORT_PREFIXES=('soccer_','tennis_','basketball_','icehockey_','baseball_','americanfootball_','mma_')
SPORT_DENY=('soccer_esports','basketball_esports','tennis_esports')
# Removed invalid The Odds API keys tennis_atp/tennis_wta. Tennis comes from odds-api.io instead.
THEODDS_SPORTS=os.getenv('THEODDS_SPORTS','soccer_epl,soccer_spain_la_liga,soccer_germany_bundesliga,basketball_nba,icehockey_nhl,baseball_mlb,americanfootball_nfl,mma_mixed_martial_arts').split(',')
ODDS_IO_BASE='https://api.odds-api.io/v3'
ODDS_IO_BOOKMAKER=os.getenv('ODDS_API_IO_BOOKMAKER','1xbet')
ODDS_IO_SPORTS=os.getenv('ODDS_IO_SPORTS','tennis,football,basketball,ice-hockey').split(',')
ODDS_IO_MAX_EVENTS=int(os.getenv('ODDS_API_IO_MAX_EVENTS','4'))
GEMINI_SHORTLIST=int(os.getenv('GEMINI_SHORTLIST','30'))
GEMINI_WATCH=int(os.getenv('GEMINI_WATCH','30'))
DIAG={'api_errors':[],'quota_exhausted':False,'cache_used':False,'cache_written':False,'odds_api_io_used':False,'odds_api_io_raw_games':0,'odds_api_io_events':0,'odds_api_io_odds_calls':0,'theodds_sports_used':0,'theodds_sport_games':0,'unique_games':0,'games_after_filter':0,'candidate_count_before_sort':0,'top_eligible_count':0,'gemini_shortlist':0,'gemini_timeout_guard':True}

def text(v):
    if isinstance(v,str): return v
    if v is None: return ''
    return json.dumps(v,ensure_ascii=False)
def as_list(v): return v if isinstance(v,list) else []
def fmt_start(v):
    if not v: return ''
    try:
        dt=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        return dt.astimezone(ZoneInfo(DISPLAY_TZ)).strftime('%Y-%m-%d %H:%M')
    except Exception: return str(v)
def ok_sport(k):
    s=str(k)
    return any(s.startswith(p) for p in SPORT_PREFIXES) and not any(s.startswith(d) for d in SPORT_DENY)
def mark_error(label,e):
    s=str(e)[:700]
    if 'OUT_OF_USAGE_CREDITS' in s or 'Usage quota' in s or 'exceeded your rate limit' in s: DIAG['quota_exhausted']=True
    DIAG['api_errors'].append({'label':label,'error':s})
def get_json(url,params=None):
    r=requests.get(url,params=params or {},timeout=60)
    if not r.ok: raise RuntimeError(f'{r.status_code} {r.text[:500]}')
    return r.json()
def safe_get(label,url,params=None):
    if DIAG['quota_exhausted'] and label.startswith('theodds'): return []
    try: return get_json(url,params)
    except Exception as e: mark_error(label,e); return []
def load_cache():
    try:
        if CACHE.exists():
            DIAG['cache_used']=True
            data=json.loads(CACHE.read_text(encoding='utf-8'))
            return data if isinstance(data,list) else []
    except Exception as e: mark_error('cache_read',e)
    return []
def save_cache(games):
    try:
        if games:
            CACHE.write_text(json.dumps(games,ensure_ascii=False),encoding='utf-8')
            DIAG['cache_written']=True
    except Exception as e: mark_error('cache_write',e)
def upcoming(g):
    try:
        t=datetime.fromisoformat(str(g.get('commence_time','')).replace('Z','+00:00'))
        h=(t-datetime.now(timezone.utc)).total_seconds()/3600
        return 0<h<=MAX_HOURS
    except Exception: return False

def odds_io_get(path,params=None):
    if not ODDS_IO: return []
    p=dict(params or {}); p['apiKey']=ODDS_IO
    return safe_get('odds-api.io',ODDS_IO_BASE+path,p)
def odds_io_pick_league(leagues,sport):
    if not isinstance(leagues,list): return None
    preferred={
        'football':['england-premier-league','spain-laliga','germany-bundesliga','denmark-superliga'],
        'tennis':['atp-atp-rome-italy-men-singles','wta-wta-rome-italy-women-singles','atp-atp-madrid-spain-men-singles','wta-wta-madrid-spain-women-singles'],
        'basketball':['usa-nba','euroleague'],
        'ice-hockey':['usa-nhl']
    }.get(sport,[])
    by_slug={x.get('slug'):x for x in leagues if isinstance(x,dict)}
    for slug in preferred:
        if slug in by_slug and int(by_slug[slug].get('eventsCount') or 0)>0: return slug
    rows=[x for x in leagues if isinstance(x,dict) and x.get('slug') and int(x.get('eventsCount') or 0)>0]
    rows=sorted(rows,key=lambda x:int(x.get('eventsCount') or 0),reverse=True)
    return rows[0].get('slug') if rows else None

def odds_io_market_to_markets(bookmakers_obj,home,away):
    markets=[]
    if not isinstance(bookmakers_obj,dict): return markets
    for bookmaker,market_list in bookmakers_obj.items():
        bmarkets=[]
        for m in market_list if isinstance(market_list,list) else []:
            name=str(m.get('name','')).lower(); rows=m.get('odds') or []
            outcomes=[]
            if name=='ml' and rows:
                row=rows[0] if isinstance(rows[0],dict) else {}
                if row.get('home'): outcomes.append({'name':home,'price':row.get('home')})
                if row.get('draw'): outcomes.append({'name':'draw','price':row.get('draw')})
                if row.get('away'): outcomes.append({'name':away,'price':row.get('away')})
                if outcomes: bmarkets.append({'key':'h2h','outcomes':outcomes})
            elif name=='spread':
                for row in rows:
                    if not isinstance(row,dict): continue
                    hdp=row.get('hdp')
                    if row.get('home'): outcomes.append({'name':home,'price':row.get('home'),'point':hdp})
                    if row.get('away'): outcomes.append({'name':away,'price':row.get('away'),'point':hdp})
                if outcomes: bmarkets.append({'key':'spreads','outcomes':outcomes})
            elif name=='totals':
                for row in rows:
                    if not isinstance(row,dict): continue
                    hdp=row.get('hdp')
                    if row.get('over'): outcomes.append({'name':'over','price':row.get('over'),'point':hdp})
                    if row.get('under'): outcomes.append({'name':'under','price':row.get('under'),'point':hdp})
                if outcomes: bmarkets.append({'key':'totals','outcomes':outcomes})
        if bmarkets: markets.append({'key':bookmaker,'markets':bmarkets})
    return markets

def normalize_odds_io_event(odds):
    if not isinstance(odds,dict): return None
    home=odds.get('home'); away=odds.get('away'); start=odds.get('date')
    books=odds_io_market_to_markets(odds.get('bookmakers'),home,away)
    if not (home and away and start and books): return None
    sport=(odds.get('sport') or {}).get('slug','football') if isinstance(odds.get('sport'),dict) else 'football'
    mapping={'football':'soccer_odds_api_io','ice-hockey':'icehockey_odds_api_io'}
    sk=mapping.get(sport,f'{sport}_odds_api_io')
    return {'id':odds.get('id'),'sport_key':sk,'home_team':home,'away_team':away,'commence_time':start,'bookmakers':books}
def fetch_odds_api_io_sport(sport):
    leagues=odds_io_get('/leagues',{'sport':sport})
    league=odds_io_pick_league(leagues,sport)
    if not league: return []
    events=odds_io_get('/events',{'sport':sport,'league':league})
    if not isinstance(events,list): return []
    DIAG['odds_api_io_events']+=len(events)
    games=[]
    for ev in events[:ODDS_IO_MAX_EVENTS]:
        eid=ev.get('id') if isinstance(ev,dict) else None
        if not eid: continue
        odds=odds_io_get('/odds',{'eventId':eid,'bookmakers':ODDS_IO_BOOKMAKER})
        DIAG['odds_api_io_odds_calls']+=1
        g=normalize_odds_io_event(odds)
        if g: games.append(g)
    if games:
        DIAG['odds_api_io_used']=True; DIAG['odds_api_io_raw_games']+=len(games)
    return games

def market_weight(market,books,point):
    base=3.0 if market=='h2h' else 1.2 if market=='totals' else 0.8 if market=='spreads' else 0
    if books>=20: base+=2.0
    elif books>=10: base+=1.0
    elif books<5: base-=1.5
    if point is not None and books<6: base-=0.8
    return base
def score_candidate(odds,median,books,market,point=None):
    edge=(odds/median)-1 if median else 0
    penalty=2.5 if odds>=5 else 1.5 if odds>=4 else 0.8 if odds>=3.5 else 0
    robust=market_weight(market,books,point)
    return round(edge*100+robust-penalty,2),edge,round(robust,2)
def deterministic_stake(odds,edge_pct,books,pre_score,market,role='PRIMARY'):
    if role!='PRIMARY': return 0
    try: odds=float(odds); edge=float(edge_pct); books=int(books or 0); pre=float(pre_score or 0)
    except Exception: return 1
    if odds>=4: return 1
    if odds>=3: return 1 if edge<7 else 2
    if odds>=2.4: return 2 if edge>=6 else 1
    if edge>=7 and books>=10 and pre>=10: return 4
    if edge>=5 and books>=8: return 3
    return 2
def is_top_eligible(c):
    try: odds=float(c.get('odds')); score=float(c.get('pre_score') or 0); edge=float(c.get('edge_pct') or 0)
    except Exception: return False
    if score<MIN_TOP_SCORE or odds>MAX_AUTO_ODDS: return False
    if odds>=4 and edge<12: return False
    return True
def conflicts(a,b):
    if a.get('event')!=b.get('event'): return False
    if a.get('market')=='h2h' and b.get('market')=='h2h': return True
    if a.get('market') in ('totals','spreads') and b.get('market')==a.get('market') and str(a.get('point'))==str(b.get('point')):
        return str(a.get('selection')).lower()!=str(b.get('selection')).lower()
    return False

def add_candidate(cands,g,market,selection,odds_list,point=None):
    if len(odds_list)<1: return
    best=max(odds_list); med=statistics.median(odds_list)
    if best<1.2 or best>8.0 or (med and best/med>2.0): return
    score,edge,robust=score_candidate(best,med,len(odds_list),market,point)
    if score<0.5: return
    cands.append({'event':f"{g.get('home_team')} vs {g.get('away_team')}",'sport':g.get('sport_key'),'start':g.get('commence_time'),'start_local':fmt_start(g.get('commence_time')),'market':market,'selection':selection,'point':point,'odds':round(best,2),'median':round(med,2),'edge_pct':round(edge*100,1),'books':len(odds_list),'spread_ratio':round(best/med,2) if med else None,'market_weight':robust,'pre_score':score})
def parse_games(raw):
    cands=[]; games_ok=0
    for g in raw:
        if not ok_sport(g.get('sport_key','')) or not upcoming(g): continue
        games_ok+=1; buckets={}
        for b in g.get('bookmakers',[]):
            for m in b.get('markets',[]):
                mk=m.get('key')
                if mk not in MARKETS: continue
                for o in m.get('outcomes',[]):
                    name=o.get('name','')
                    if str(name).lower()=='draw': continue
                    try: price=float(o['price'])
                    except Exception: continue
                    buckets.setdefault((mk,name,o.get('point')),[]).append(price)
        for (mk,name,point),prices in buckets.items(): add_candidate(cands,g,mk,name,prices,point)
    DIAG['games_after_filter']=games_ok; DIAG['candidate_count_before_sort']=len(cands)
    return cands

def collect_candidates():
    all_games=[]
    if ODDS:
        for sport in [s.strip() for s in THEODDS_SPORTS if s.strip()]:
            data=safe_get(f'theodds:{sport}',f'https://api.the-odds-api.com/v4/sports/{sport}/odds',{'apiKey':ODDS,'regions':'eu,uk','markets':','.join(MARKETS),'oddsFormat':'decimal'})
            if isinstance(data,list): all_games+=data
        DIAG['theodds_sports_used']=len([s for s in THEODDS_SPORTS if s.strip()]); DIAG['theodds_sport_games']=len(all_games)
    if ODDS_IO:
        for sport in [s.strip() for s in ODDS_IO_SPORTS if s.strip()]:
            all_games+=fetch_odds_api_io_sport(sport)
    if all_games and not DIAG['quota_exhausted']: save_cache(all_games)
    if not all_games: all_games=load_cache()
    seen=set(); uniq=[]
    for g in all_games:
        gid=g.get('id') or (g.get('sport_key'),g.get('commence_time'),g.get('home_team'),g.get('away_team'))
        if str(gid) in seen: continue
        seen.add(str(gid)); uniq.append(g)
    DIAG['unique_games']=len(uniq)
    out=sorted(parse_games(uniq),key=lambda x:(x['pre_score'],x['books'],x['edge_pct']),reverse=True)
    DIAG['top_eligible_count']=len([c for c in out if is_top_eligible(c)])
    return out

def pre_resolve(cands):
    selected=[]; watch=[]
    for c in cands:
        if any(conflicts(c,s) for s in selected): watch.append({**c,'conflict_status':'market_conflict'}); continue
        selected.append({**c,'conflict_status':'clear'})
    return selected,watch
def fallback_rank(cands):
    out=[]; seen=set()
    for c in [x for x in cands if is_top_eligible(x)]:
        if c.get('event') in seen: continue
        out.append({'event':c['event'],'market':c['market'],'pick':c['selection'],'point':c.get('point'),'odds':c['odds'],'confidence':'auto','role':'PRIMARY','reason':f"Auto-valgt: score {c.get('pre_score')}, edge {c.get('edge_pct')}%, books {c.get('books')}."})
        seen.add(c.get('event'))
        if len(out)>=MAX_TOP_BETS: break
    return out

def gemini_rank(cands,conflict_watch):
    shortlist=[c for c in cands if is_top_eligible(c)][:GEMINI_SHORTLIST]
    watch_seed=([c for c in cands if not is_top_eligible(c)][:GEMINI_WATCH]+conflict_watch[:GEMINI_WATCH])[:GEMINI_WATCH]
    DIAG['gemini_shortlist']=len(shortlist)
    if not GEMINI or not shortlist: return {'summary':'fallback ranking','top_bets':fallback_rank(cands),'watchlist':watch_seed,'pass':[]}
    slim=[{k:x.get(k) for k in ['event','sport','start_local','market','selection','point','odds','edge_pct','books','pre_score']} for x in shortlist]
    prompt='''V7 Top Bet Governor. Pick max 20 singles. Max 1 pr event. JSON only: {"summary":"...","top_bets":[],"watchlist":[],"pass":[]}. Item fields: event, market, pick, point, odds, confidence, role, reason. Data:\n'''+json.dumps(slim,ensure_ascii=False)
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}'
    try:
        r=requests.post(url,json={'contents':[{'parts':[{'text':prompt}]}]},timeout=45); r.raise_for_status()
        txt=r.json()['candidates'][0]['content']['parts'][0]['text']; m=re.search(r'\{.*\}',txt,re.S)
        if m: return json.loads(m.group(0))
    except Exception as e:
        return {'summary':f'Gemini skipped/fallback: {e}','top_bets':fallback_rank(cands),'watchlist':watch_seed,'pass':[]}
    return {'summary':'No parse/fallback','top_bets':fallback_rank(cands),'watchlist':watch_seed,'pass':[]}

def normalize_item(x):
    if not isinstance(x,dict): return None
    if 'selection' in x and 'pick' not in x: x['pick']=x.get('selection')
    return x
def apply_candidate_metrics(item,lookup):
    key=(item.get('event'),item.get('market'),str(item.get('pick')),str(item.get('point')))
    c=lookup.get(key)
    if c:
        for k in ['edge_pct','books','pre_score','median','market_weight','sport','start','start_local']: item[k]=c.get(k)
    return item
def sanitize(res,all_candidates):
    lookup={(c.get('event'),c.get('market'),str(c.get('selection')),str(c.get('point'))):c for c in all_candidates}
    if not isinstance(res,dict): res={}
    for sec in ['top_bets','watchlist','pass']:
        res[sec]=[normalize_item(x) for x in as_list(res.get(sec))]
        res[sec]=[x for x in res[sec] if isinstance(x,dict)]
    top=res['top_bets'] if 0<len(res['top_bets'])<=MAX_TOP_BETS else fallback_rank(all_candidates)
    clean=[]; seen=set(); moved=[]
    for x in top:
        x=apply_candidate_metrics(x,lookup); event=x.get('event')
        try: odds=float(str(x.get('odds')).replace(',','.'))
        except Exception: continue
        if event in seen:
            x['stake_kr']=0; x['role']='WATCHLIST'; moved.append(x); continue
        x['role']='PRIMARY'; x['stake_kr']=deterministic_stake(odds,x.get('edge_pct',0),x.get('books',0),x.get('pre_score',0),x.get('market'),'PRIMARY')
        clean.append(x); seen.add(event)
        if len(clean)>=MAX_TOP_BETS: break
    watch=[]
    for x in moved+res['watchlist']:
        x=apply_candidate_metrics(x,lookup); x['stake_kr']=0; x['role']='WATCHLIST'; watch.append(x)
    for x in res['pass']: x['stake_kr']=0
    res['top_bets']=sorted(clean,key=lambda x:(float(x.get('pre_score') or 0),int(x.get('books') or 0)),reverse=True)
    res['watchlist']=watch[:80]; res['pass']=res['pass'][:80]
    res['summary']=text(res.get('summary')) or ('ingen spil nu' if not clean else f'{len(clean)} primary top bets')
    return res

raw_cands=collect_candidates(); resolved,conflict_watch=pre_resolve(raw_cands); res=sanitize(gemini_rank(resolved,conflict_watch),raw_cands)
if DIAG.get('cache_used'): res['summary']='CACHE/STale odds used. '+text(res.get('summary'))
if DIAG.get('odds_api_io_used'): res['summary']='odds-api.io included. '+text(res.get('summary'))
res['mode']=MODE; res['candidate_count']=len(raw_cands); res['resolved_count']=len(resolved); res['conflict_watch_count']=len(conflict_watch); res['diagnostics']=DIAG
res['top_bet_governor']={'max_top_bets':MAX_TOP_BETS,'min_top_score':MIN_TOP_SCORE,'max_auto_odds':MAX_AUTO_ODDS,'gemini_shortlist':GEMINI_SHORTLIST,'display_tz':DISPLAY_TZ}
(OUT/'v6_expansion_engine.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'v6_expansion_engine.md','w',encoding='utf-8') as f:
    f.write('# V7 MULTI-SPORT ENGINE — FIXED\n\n'+text(res.get('summary'))+f"\n\nCandidates scanned: {len(raw_cands)} | Resolved: {len(resolved)} | Conflict watchlist: {len(conflict_watch)} | Governor max top bets: {MAX_TOP_BETS} | Timezone: {DISPLAY_TZ}\n\n")
    f.write('## DIAGNOSTICS\n```json\n'+json.dumps(DIAG,ensure_ascii=False,indent=2)+'\n```\n\n')
    for sec in ['top_bets','watchlist','pass']:
        f.write('## '+sec.upper()+'\n')
        for i,x in enumerate(as_list(res.get(sec)),1):
            f.write(f"{i}. {x.get('event')} | start {x.get('start_local') or fmt_start(x.get('start'))} | sport {x.get('sport')} | {x.get('market')} | {x.get('pick')} | {x.get('point')} | odds {x.get('odds')} | stake {x.get('stake_kr')} | role {x.get('role')} | edge {x.get('edge_pct')} | books {x.get('books')} | score {x.get('pre_score')} | conf {x.get('confidence')} | {text(x.get('reason'))}\n")
        f.write('\n')
print(text(res.get('summary')))
