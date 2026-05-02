import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
CACHE=OUT/'odds_cache_raw.json'
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
ODDS_IO=os.getenv('ODDS_API_IO_KEY','')
MODEL='gemini-2.5-flash'
MODE='V6_ODDS_API_IO_INTEGRATION_SHOW_KICKOFF'
MAX_HOURS=168
MAX_TOP_BETS=12
MIN_TOP_SCORE=8.0
MAX_AUTO_ODDS=6.0
LOW_CREDIT_MODE=os.getenv('LOW_CREDIT_MODE','1')=='1'
MARKETS=('h2h','spreads','totals')
SPORT_PREFIXES=('tennis_','basketball_','icehockey_','soccer_')
SPORT_DENY=('soccer_esports','basketball_esports','tennis_esports')
ODDS_IO_BASE='https://api.odds-api.io/v3'
ODDS_IO_BOOKMAKER=os.getenv('ODDS_API_IO_BOOKMAKER','1xbet')
ODDS_IO_SPORT=os.getenv('ODDS_API_IO_SPORT','football')
ODDS_IO_MAX_EVENTS=int(os.getenv('ODDS_API_IO_MAX_EVENTS','8'))
DISPLAY_TZ=os.getenv('DISPLAY_TZ','Europe/Copenhagen')
DIAG={'api_errors':[],'quota_exhausted':False,'cache_used':False,'cache_written':False,'odds_api_io_used':False,'odds_api_io_raw_games':0,'odds_api_io_events':0,'odds_api_io_odds_calls':0,'sports_found':0,'sports_used':0,'upcoming_raw_games':0,'sport_endpoint_raw_games':0,'unique_games':0,'games_after_filter':0,'candidate_count_before_sort':0,'top_eligible_count':0}

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
    except Exception:
        return str(v)
def ok_sport(k): return any(str(k).startswith(p) for p in SPORT_PREFIXES) and not any(str(k).startswith(d) for d in SPORT_DENY)
def mark_error(label,e):
    s=str(e)[:700]
    if 'OUT_OF_USAGE_CREDITS' in s or 'Usage quota has been reached' in s: DIAG['quota_exhausted']=True
    DIAG['api_errors'].append({'label':label,'error':s})
def get_json(url,params=None,headers=None):
    r=requests.get(url,params=params or {},headers=headers or {},timeout=60)
    if not r.ok: raise RuntimeError(f'{r.status_code} {r.text[:500]}')
    return r.json()
def safe_get(label,url,params=None,headers=None):
    if DIAG['quota_exhausted'] and label.startswith('theodds'): return []
    try: return get_json(url,params,headers)
    except Exception as e: mark_error(label,e); return []
def load_cache():
    try:
        if CACHE.exists():
            data=json.loads(CACHE.read_text(encoding='utf-8'))
            DIAG['cache_used']=True
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

def list_sports():
    if LOW_CREDIT_MODE: return []
    if not ODDS:
        mark_error('secrets','Missing THE_ODDS_API_KEY'); return []
    sports=safe_get('theodds:sports','https://api.the-odds-api.com/v4/sports',{'apiKey':ODDS})
    out=[s.get('key') for s in sports if isinstance(s,dict) and s.get('active') and ok_sport(s.get('key',''))]
    DIAG['sports_found']=len(out)
    return out

def odds_io_get(path,params=None):
    p=dict(params or {}); p['apiKey']=ODDS_IO
    return safe_get('odds-api.io',ODDS_IO_BASE+path,p)

def odds_io_pick_league(leagues):
    if not isinstance(leagues,list): return None
    preferred=['england-premier-league','spain-laliga','italy-serie-a','germany-bundesliga','france-ligue-1','denmark-superliga','usa-mls','argentina-liga-profesional']
    by_slug={x.get('slug'):x for x in leagues if isinstance(x,dict)}
    for slug in preferred:
        if slug in by_slug and int(by_slug[slug].get('eventsCount') or 0)>0: return slug
    rows=[x for x in leagues if isinstance(x,dict) and x.get('slug') and int(x.get('eventsCount') or 0)>0]
    rows=sorted(rows,key=lambda x:int(x.get('eventsCount') or 0),reverse=True)
    return rows[0].get('slug') if rows else None

def odds_io_market_to_markets(bookmakers_obj, home, away):
    markets=[]
    if not isinstance(bookmakers_obj,dict): return markets
    for bookmaker, market_list in bookmakers_obj.items():
        bmarkets=[]
        for m in market_list if isinstance(market_list,list) else []:
            name=str(m.get('name','')).lower()
            odds_rows=m.get('odds') or []
            if not odds_rows: continue
            outcomes=[]
            if name=='ml':
                row=odds_rows[0] if isinstance(odds_rows[0],dict) else {}
                if row.get('home'): outcomes.append({'name':home,'price':row.get('home')})
                if row.get('draw'): outcomes.append({'name':'draw','price':row.get('draw')})
                if row.get('away'): outcomes.append({'name':away,'price':row.get('away')})
                if outcomes: bmarkets.append({'key':'h2h','outcomes':outcomes})
            elif name=='spread':
                for row in odds_rows:
                    if not isinstance(row,dict): continue
                    hdp=row.get('hdp')
                    if row.get('home'): outcomes.append({'name':home,'price':row.get('home'),'point':hdp})
                    if row.get('away'): outcomes.append({'name':away,'price':row.get('away'),'point':hdp})
                if outcomes: bmarkets.append({'key':'spreads','outcomes':outcomes})
            elif name=='totals':
                for row in odds_rows:
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
    sk='soccer_odds_api_io' if sport=='football' else f'{sport}_odds_api_io'
    return {'id':odds.get('id'),'sport_key':sk,'home_team':home,'away_team':away,'commence_time':start,'bookmakers':books}

def fetch_odds_api_io():
    if not ODDS_IO:
        mark_error('secrets','Missing ODDS_API_IO_KEY'); return []
    leagues=odds_io_get('/leagues',{'sport':ODDS_IO_SPORT})
    league=odds_io_pick_league(leagues)
    if not league:
        mark_error('odds-api.io','No usable league found'); return []
    events=odds_io_get('/events',{'sport':ODDS_IO_SPORT,'league':league})
    if not isinstance(events,list): return []
    DIAG['odds_api_io_events']=len(events)
    games=[]
    for ev in events[:ODDS_IO_MAX_EVENTS]:
        eid=ev.get('id') if isinstance(ev,dict) else None
        if not eid: continue
        odds=odds_io_get('/odds',{'eventId':eid,'bookmakers':ODDS_IO_BOOKMAKER})
        DIAG['odds_api_io_odds_calls']+=1
        g=normalize_odds_io_event(odds)
        if g: games.append(g)
    if games:
        DIAG['odds_api_io_used']=True; DIAG['odds_api_io_raw_games']=len(games)
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
    variance_penalty=2.5 if odds>=5 else 1.5 if odds>=4 else 0.8 if odds>=3.5 else 0
    robust_bonus=market_weight(market,books,point)
    return round(edge*100 + robust_bonus - variance_penalty,2), edge, round(robust_bonus,2)

def deterministic_stake(odds,edge_pct,books,pre_score,market,role='PRIMARY'):
    if role!='PRIMARY': return 0
    try: odds=float(odds); edge=float(edge_pct); books=int(books or 0); pre=float(pre_score or 0)
    except Exception: return 1
    if market!='h2h' and books<8: return 1
    if odds>=4.0: return 1
    if odds>=3.5: return 1 if edge<10 else 2
    if odds>=3.0: return 1 if edge<7 else 2
    if odds>=2.4: return 2 if edge>=6 and books>=8 else 1
    if odds>=1.8:
        if market=='h2h' and edge>=7 and books>=10 and pre>=10: return 4
        if edge>=5 and books>=8: return 3
        return 2
    if odds>=1.35:
        if market=='h2h' and edge>=6 and books>=10 and pre>=10: return 4
        if edge>=4 and books>=8: return 3
        return 2
    return 1

def is_top_eligible(c):
    try: odds=float(c.get('odds')); score=float(c.get('pre_score') or 0); edge=float(c.get('edge_pct') or 0)
    except Exception: return False
    if score < MIN_TOP_SCORE: return False
    if odds > MAX_AUTO_ODDS: return False
    if odds >= 4.0 and edge < 12: return False
    return True

def conflicts(a,b):
    if a.get('event')!=b.get('event'): return False
    if a.get('market')=='h2h' and b.get('market')=='h2h': return True
    if a.get('market')=='totals' and b.get('market')=='totals' and str(a.get('point'))==str(b.get('point')):
        return str(a.get('selection')).lower()!=str(b.get('selection')).lower()
    if a.get('market')=='spreads' and b.get('market')=='spreads' and str(a.get('point'))==str(b.get('point')):
        return str(a.get('selection')).lower()!=str(b.get('selection')).lower()
    return False

def add_candidate(cands,g,market,selection,odds_list,point=None):
    if len(odds_list)<1: return
    best=max(odds_list); med=statistics.median(odds_list)
    if best<1.20 or best>8.0: return
    spread_ratio=best/med if med else 99
    if spread_ratio>2.0: return
    score,edge,robust=score_candidate(best,med,len(odds_list),market,point)
    if score<0.5: return
    cands.append({'event':f"{g.get('home_team')} vs {g.get('away_team')}",'sport':g.get('sport_key'),'start':g.get('commence_time'),'start_local':fmt_start(g.get('commence_time')),'market':market,'selection':selection,'point':point,'odds':round(best,2),'median':round(med,2),'edge_pct':round(edge*100,1),'books':len(odds_list),'spread_ratio':round(spread_ratio,2),'market_weight':robust,'pre_score':score})

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
        up=safe_get('theodds:upcoming','https://api.the-odds-api.com/v4/sports/upcoming/odds',{'apiKey':ODDS,'regions':'eu,uk','markets':','.join(MARKETS),'oddsFormat':'decimal'})
        DIAG['upcoming_raw_games']=len(up) if isinstance(up,list) else 0
        if isinstance(up,list): all_games+=up
        if all_games and not DIAG['quota_exhausted']: save_cache(all_games)
    if not all_games:
        alt=fetch_odds_api_io()
        if alt: all_games=alt; save_cache(all_games)
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
        out.append({'event':c['event'],'market':c['market'],'pick':c['selection'],'point':c.get('point'),'odds':c['odds'],'confidence':'auto','role':'PRIMARY','reason':f"Auto-valgt af Top Bet Governor: score {c.get('pre_score')}, edge {c.get('edge_pct')}%, books {c.get('books')}."})
        seen.add(c.get('event'))
        if len(out)>=MAX_TOP_BETS: break
    return out

def gemini_rank(cands,conflict_watch):
    shortlist=[c for c in cands if is_top_eligible(c)][:60]
    watch_seed=[c for c in cands if not is_top_eligible(c)][:80]+conflict_watch[:80]
    if not GEMINI: return {'summary':'Missing GEMINI_API_KEY','top_bets':fallback_rank(cands),'watchlist':watch_seed[:80],'pass':[]}
    prompt='''Du er Bendix V6 Top Bet Governor. Singles only, ingen livebetting, ingen parlays. Maks 12 top_bets, maks 1 pr event. Returner dansk JSON only: summary, top_bets, watchlist, pass. Hvert item: event, market, pick, point, odds, confidence, role, reason. Data:\n'''+json.dumps({'shortlist_count':len(shortlist),'shortlist':shortlist,'watch_seed':watch_seed[:80]},ensure_ascii=False)
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}'
    try:
        r=requests.post(url,json={"contents":[{"parts":[{"text":prompt}]}]},timeout=90); r.raise_for_status()
        txt=r.json()['candidates'][0]['content']['parts'][0]['text']
        m=re.search(r'\{.*\}',txt,re.S)
        if m: return json.loads(m.group(0))
    except Exception as e:
        return {'summary':f'Gemini error: {e}','top_bets':fallback_rank(cands),'watchlist':watch_seed[:80],'pass':[]}
    return {'summary':'No parse','top_bets':fallback_rank(cands),'watchlist':watch_seed[:80],'pass':[]}

def normalize_item(x):
    if not isinstance(x,dict): return None
    if 'selection' in x and 'pick' not in x: x['pick']=x.get('selection')
    return x

def apply_candidate_metrics(item, lookup):
    key=(item.get('event'), item.get('market'), str(item.get('pick')), str(item.get('point')))
    c=lookup.get(key)
    if c:
        for k in ['edge_pct','books','pre_score','median','market_weight','sport','start','start_local']: item[k]=c.get(k)
    return item

def sanitize(res, all_candidates):
    lookup={(c.get('event'),c.get('market'),str(c.get('selection')),str(c.get('point'))):c for c in all_candidates}
    if not isinstance(res,dict): res={}
    for sec in ['top_bets','watchlist','pass']:
        res[sec]=[normalize_item(x) for x in as_list(res.get(sec))]
        res[sec]=[x for x in res[sec] if isinstance(x,dict)]
    top=res['top_bets']
    if len(top)==0 or len(top)>MAX_TOP_BETS: top=fallback_rank(all_candidates)
    clean=[]; seen_events=set(); moved=[]
    for x in top:
        x=apply_candidate_metrics(x,lookup); event=x.get('event')
        try: odds=float(str(x.get('odds')).replace(',','.'))
        except Exception: continue
        if event in seen_events:
            x['stake_kr']=0; x['role']='WATCHLIST'; moved.append(x); continue
        x['role']='PRIMARY'; x['stake_kr']=deterministic_stake(odds,x.get('edge_pct',0),x.get('books',0),x.get('pre_score',0),x.get('market'),'PRIMARY')
        clean.append(x); seen_events.add(event)
        if len(clean)>=MAX_TOP_BETS: break
    watch=[]
    for x in moved+res['watchlist']:
        x=apply_candidate_metrics(x,lookup); x['stake_kr']=0; x['role']='WATCHLIST'; watch.append(x)
    for x in res['pass']: x['stake_kr']=0
    res['top_bets']=sorted(clean,key=lambda x:(float(x.get('pre_score') or 0), int(x.get('books') or 0)),reverse=True)
    res['watchlist']=watch[:80]; res['pass']=res['pass'][:80]
    res['summary']=text(res.get('summary')) or ('ingen spil nu' if not clean else f'{len(clean)} primary top bets')
    return res

raw_cands=collect_candidates(); resolved,conflict_watch=pre_resolve(raw_cands); res=sanitize(gemini_rank(resolved,conflict_watch),raw_cands)
if DIAG.get('cache_used'): res['summary']='CACHE/STale odds used. '+text(res.get('summary'))
if DIAG.get('odds_api_io_used'): res['summary']='odds-api.io fallback used. '+text(res.get('summary'))
res['mode']=MODE; res['candidate_count']=len(raw_cands); res['resolved_count']=len(resolved); res['conflict_watch_count']=len(conflict_watch); res['diagnostics']=DIAG
res['top_bet_governor']={'max_top_bets':MAX_TOP_BETS,'min_top_score':MIN_TOP_SCORE,'max_auto_odds':MAX_AUTO_ODDS,'low_credit_mode':LOW_CREDIT_MODE,'odds_api_io_bookmaker':ODDS_IO_BOOKMAKER,'display_tz':DISPLAY_TZ}
(OUT/'v6_expansion_engine.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'v6_expansion_engine.md','w',encoding='utf-8') as f:
    f.write('# V6 EXPANSION ENGINE — ODDS-API.IO INTEGRATION + KICKOFF\n\n'+text(res.get('summary'))+f"\n\nCandidates scanned: {len(raw_cands)} | Resolved: {len(resolved)} | Conflict watchlist: {len(conflict_watch)} | Governor max top bets: {MAX_TOP_BETS} | Timezone: {DISPLAY_TZ}\n\n")
    f.write('## DIAGNOSTICS\n```json\n'+json.dumps(DIAG,ensure_ascii=False,indent=2)+'\n```\n\n')
    for sec in ['top_bets','watchlist','pass']:
        f.write('## '+sec.upper()+'\n')
        for i,x in enumerate(as_list(res.get(sec)),1): f.write(f"{i}. {x.get('event')} | start {x.get('start_local') or fmt_start(x.get('start'))} | {x.get('market')} | {x.get('pick')} | {x.get('point')} | odds {x.get('odds')} | stake {x.get('stake_kr')} | role {x.get('role')} | edge {x.get('edge_pct')} | books {x.get('books')} | market_weight {x.get('market_weight')} | score {x.get('pre_score')} | conf {x.get('confidence')} | {text(x.get('reason'))}\n")
        f.write('\n')
print(text(res.get('summary')))
