import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

OUT = pathlib.Path('output'); OUT.mkdir(exist_ok=True)
CACHE = OUT / 'odds_cache_raw.json'
GEMINI = os.getenv('GEMINI_API_KEY','')
THE_ODDS = os.getenv('THE_ODDS_API_KEY','')
ODDS_IO = os.getenv('ODDS_API_IO_KEY','')
MODEL = os.getenv('GEMINI_MODEL','gemini-2.5-flash')
DISPLAY_TZ = os.getenv('DISPLAY_TZ','Europe/Copenhagen')
MAX_HOURS = int(os.getenv('MAX_HOURS','168'))
MAX_TOP_BETS = int(os.getenv('MAX_TOP_BETS','20'))
THEODDS_SPORTS = os.getenv('THEODDS_SPORTS','soccer_epl,soccer_spain_la_liga,soccer_germany_bundesliga,basketball_nba,icehockey_nhl,baseball_mlb,americanfootball_nfl,mma_mixed_martial_arts').split(',')
ODDS_IO_SPORTS = os.getenv('ODDS_IO_SPORTS','football,basketball,ice-hockey,tennis').split(',')
ODDS_IO_BOOKMAKER = os.getenv('ODDS_API_IO_BOOKMAKER','1xbet')
ODDS_IO_MAX_EVENTS = int(os.getenv('ODDS_API_IO_MAX_EVENTS','8'))
MARKETS = ('h2h','spreads','totals')
MODE = 'V11_RESILIENT_MULTI_SOURCE_ENGINE'

SPORT_CAPS = {'soccer':7,'baseball':4,'basketball':4,'icehockey':4,'mma':2,'tennis':3,'americanfootball':3,'other':2}
MAX_LONGSHOT_TOP = int(os.getenv('MAX_LONGSHOT_TOP','3'))
MAX_LOW_CONF_TOP = int(os.getenv('MAX_LOW_CONF_TOP','6'))

DIAG = {
    'api_errors': [], 'quota_exhausted': False,
    'theodds_games': 0, 'odds_api_io_events': 0, 'odds_api_io_games': 0,
    'candidate_count': 0, 'top_count': 0,
    'engine_note': 'The Odds API is preferred. odds-api.io is used as fallback and can create conservative low-confidence paper picks.'
}

def now_iso(): return datetime.now(timezone.utc).isoformat()
def text(v): return v if isinstance(v,str) else json.dumps(v,ensure_ascii=False)
def as_list(v): return v if isinstance(v,list) else []
def dt(v):
    try: return datetime.fromisoformat(str(v).replace('Z','+00:00'))
    except Exception: return None

def fmt_start(v):
    d = dt(v)
    return d.astimezone(ZoneInfo(DISPLAY_TZ)).strftime('%Y-%m-%d %H:%M') if d else str(v or '')

def upcoming(v):
    d = dt(v)
    if not d: return False
    h = (d - datetime.now(timezone.utc)).total_seconds()/3600
    return 0 < h <= MAX_HOURS

def sport_bucket(s):
    s = str(s or '').lower()
    if s.startswith('soccer_') or s == 'football': return 'soccer'
    if s.startswith('baseball_'): return 'baseball'
    if s.startswith('basketball_') or s == 'basketball': return 'basketball'
    if s.startswith('icehockey_') or s == 'ice-hockey': return 'icehockey'
    if s.startswith('mma_'): return 'mma'
    if s.startswith('tennis_') or s == 'tennis': return 'tennis'
    if s.startswith('americanfootball_'): return 'americanfootball'
    return 'other'

def mark_error(label,e):
    s = str(e)[:700]
    if 'OUT_OF_USAGE_CREDITS' in s or 'Usage quota' in s:
        DIAG['quota_exhausted'] = True
    DIAG['api_errors'].append({'label':label,'error':s})

def get_json(url, params=None, headers=None):
    r = requests.get(url, params=params or {}, headers=headers or {}, timeout=60)
    if not r.ok:
        raise RuntimeError(f'{r.status_code} {r.text[:500]}')
    return r.json()

def safe_get(label,url,params=None,headers=None):
    try: return get_json(url,params,headers)
    except Exception as e: mark_error(label,e); return []

# ---------- DATA SOURCES ----------
def fetch_theodds():
    if not THE_ODDS: return []
    games=[]
    for sport in [s.strip() for s in THEODDS_SPORTS if s.strip()]:
        data = safe_get('theodds:'+sport, f'https://api.the-odds-api.com/v4/sports/{sport}/odds', {
            'apiKey': THE_ODDS, 'regions':'eu,uk', 'markets': ','.join(MARKETS), 'oddsFormat':'decimal'
        })
        if isinstance(data,list):
            for g in data:
                if upcoming(g.get('commence_time')):
                    g['source'] = 'the-odds-api'
                    games.append(g)
    DIAG['theodds_games'] = len(games)
    return games

def odds_io_get(path,params=None):
    if not ODDS_IO: return []
    p = dict(params or {}); p['apiKey'] = ODDS_IO
    return safe_get('odds-api.io', 'https://api.odds-api.io/v3'+path, p)

def odds_io_pick_leagues(sport):
    preferred = {
        'football':['england-premier-league','spain-laliga','germany-bundesliga','denmark-superliga'],
        'basketball':['usa-nba','euroleague'],
        'ice-hockey':['usa-nhl'],
        'tennis':['atp-atp-rome-italy-men-singles','wta-wta-rome-italy-women-singles']
    }.get(sport, [])
    leagues = odds_io_get('/leagues', {'sport':sport})
    by = {x.get('slug'):x for x in leagues if isinstance(x,dict)}
    out=[]
    for slug in preferred:
        if slug in by and int(by[slug].get('eventsCount') or 0)>0: out.append(slug)
    if len(out) < 2:
        rows=[x for x in leagues if isinstance(x,dict) and x.get('slug') and int(x.get('eventsCount') or 0)>0]
        rows=sorted(rows,key=lambda x:int(x.get('eventsCount') or 0),reverse=True)
        out += [x.get('slug') for x in rows[:2] if x.get('slug') not in out]
    return out[:4]

def odds_io_markets(odds, home, away):
    books=[]
    bobj=odds.get('bookmakers') if isinstance(odds,dict) else {}
    if not isinstance(bobj,dict): return []
    for bookmaker, rows in bobj.items():
        markets=[]
        for m in rows if isinstance(rows,list) else []:
            name=str(m.get('name','')).lower(); odds_rows=m.get('odds') or []
            outs=[]
            if name == 'ml' and odds_rows:
                row=odds_rows[0]
                if row.get('home'): outs.append({'name':home,'price':row.get('home')})
                if row.get('away'): outs.append({'name':away,'price':row.get('away')})
                if row.get('draw'): outs.append({'name':'draw','price':row.get('draw')})
                if outs: markets.append({'key':'h2h','outcomes':outs})
            elif name == 'totals':
                for row in odds_rows:
                    if row.get('over'): outs.append({'name':'Over','price':row.get('over'),'point':row.get('hdp')})
                    if row.get('under'): outs.append({'name':'Under','price':row.get('under'),'point':row.get('hdp')})
                if outs: markets.append({'key':'totals','outcomes':outs})
            elif name == 'spread':
                for row in odds_rows:
                    if row.get('home'): outs.append({'name':home,'price':row.get('home'),'point':row.get('hdp')})
                    if row.get('away'): outs.append({'name':away,'price':row.get('away'),'point':row.get('hdp')})
                if outs: markets.append({'key':'spreads','outcomes':outs})
        if markets: books.append({'key':bookmaker,'markets':markets})
    return books

def fetch_odds_io():
    if not ODDS_IO: return []
    games=[]
    for sport in [s.strip() for s in ODDS_IO_SPORTS if s.strip()]:
        for league in odds_io_pick_leagues(sport):
            events=odds_io_get('/events', {'sport':sport,'league':league})
            DIAG['odds_api_io_events'] += len(events) if isinstance(events,list) else 0
            for ev in as_list(events)[:ODDS_IO_MAX_EVENTS]:
                if not upcoming(ev.get('date')): continue
                oid=ev.get('id')
                if not oid: continue
                odds=odds_io_get('/odds', {'eventId':oid,'bookmakers':ODDS_IO_BOOKMAKER})
                home, away = odds.get('home') or ev.get('home'), odds.get('away') or ev.get('away')
                books=odds_io_markets(odds,home,away)
                if not books: continue
                mapped = {'football':'soccer_odds_api_io','basketball':'basketball_odds_api_io','ice-hockey':'icehockey_odds_api_io','tennis':'tennis_odds_api_io'}.get(sport, sport+'_odds_api_io')
                games.append({'id':'oddsio_'+str(oid),'source':'odds-api.io','sport_key':mapped,'home_team':home,'away_team':away,'commence_time':odds.get('date') or ev.get('date'),'bookmakers':books})
    DIAG['odds_api_io_games'] = len(games)
    return games

# ---------- CANDIDATES ----------
def add_candidate(cands,g,market,selection,prices,point=None):
    vals=[]
    for p in prices:
        try:
            fp=float(p)
            if 1.2 <= fp <= 8: vals.append(fp)
        except Exception: pass
    if not vals: return
    best=max(vals); med=statistics.median(vals); books=len(vals); src=g.get('source') or 'unknown'
    single_source = books < 2
    if single_source:
        # No median edge possible. Keep conservative paper-test picks only.
        edge=0.0
        base = 6.2 if market=='h2h' and 1.45 <= best <= 3.4 else 5.7 if market=='totals' and 1.55 <= best <= 2.4 else 4.0
        if best >= 4: base -= 2.5
        if market == 'spreads': base -= 1.0
        score=round(base,2)
        confidence='low_single_source'
    else:
        if med and best/med > 2.0: return
        edge=(best/med)-1 if med else 0
        score=edge*100 + (3 if market=='h2h' else 1.2) + (2 if books>=20 else 1 if books>=8 else 0)
        if best>=5: score-=2.5
        elif best>=4: score-=1.5
        elif best>=3.5: score-=0.8
        confidence='market_consensus'
    if score < 5.5: return
    cands.append({
        'event': f"{g.get('home_team')} vs {g.get('away_team')}", 'event_id': g.get('id'),
        'source': src, 'sport': g.get('sport_key'), 'sport_bucket': sport_bucket(g.get('sport_key')),
        'start': g.get('commence_time'), 'start_local': fmt_start(g.get('commence_time')),
        'market': market, 'selection': selection, 'point': point,
        'odds': round(best,2), 'median': round(med,2), 'edge_pct': round(edge*100,1),
        'books': books, 'pre_score': round(score,2), 'confidence': confidence,
        'single_source': single_source
    })

def parse_games(games):
    cands=[]
    for g in games:
        buckets={}
        for b in as_list(g.get('bookmakers')):
            for m in as_list(b.get('markets')):
                mk=m.get('key')
                if mk not in MARKETS: continue
                for o in as_list(m.get('outcomes')):
                    name=o.get('name')
                    if str(name).lower() == 'draw': continue
                    buckets.setdefault((mk,name,o.get('point')),[]).append(o.get('price'))
        for (mk,name,point),prices in buckets.items():
            add_candidate(cands,g,mk,name,prices,point)
    DIAG['candidate_count'] = len(cands)
    return sorted(cands,key=lambda x:(x['pre_score'],x['books'],x['odds']),reverse=True)

def collect_candidates():
    games = fetch_theodds()
    if games:
        try: CACHE.write_text(json.dumps(games,ensure_ascii=False),encoding='utf-8')
        except Exception: pass
    oddsio = fetch_odds_io()
    games += oddsio
    seen=set(); uniq=[]
    for g in games:
        key=(g.get('id'),g.get('sport_key'),g.get('home_team'),g.get('away_team'),g.get('commence_time'))
        if str(key) in seen: continue
        seen.add(str(key)); uniq.append(g)
    return parse_games(uniq)

# ---------- RANKING ----------
def top_eligible(c):
    odds=float(c.get('odds') or 0); score=float(c.get('pre_score') or 0)
    if odds > 6: return False
    if c.get('single_source') and (score < 5.7 or odds > 3.6): return False
    if not c.get('single_source') and score < 7: return False
    return True

def conflicts(a,b):
    if a.get('event') != b.get('event'): return False
    if a.get('market') == 'h2h' and b.get('market') == 'h2h': return True
    if a.get('market') == b.get('market') and str(a.get('point')) == str(b.get('point')): return True
    return False

def unit_stake(c):
    odds=float(c.get('odds') or 0); score=float(c.get('pre_score') or 0); books=int(c.get('books') or 0)
    if c.get('single_source'): return 1
    if books < 8 or odds >= 4: return 1
    if odds >= 3: return 2 if score >= 12 else 1
    if score >= 14 and books >= 10: return 4
    if score >= 10: return 3
    return 2

def risk_accept(c,counts):
    b=sport_bucket(c.get('sport')); odds=float(c.get('odds') or 0)
    if counts['sport'].get(b,0) >= SPORT_CAPS.get(b,2): return False, 'sport_cap_'+b
    if odds>=4 and counts['longshot']>=MAX_LONGSHOT_TOP: return False, 'longshot_cap'
    if c.get('single_source') and counts['single_source']>=MAX_LOW_CONF_TOP: return False, 'single_source_cap'
    return True,''

def rank(cands):
    top=[]; watch=[]; counts={'sport':{},'longshot':0,'single_source':0}
    for c in cands:
        item={'event':c['event'],'event_id':c.get('event_id'),'source':c.get('source'),'sport':c.get('sport'),'sport_bucket':c.get('sport_bucket'),'start':c.get('start'),'start_local':c.get('start_local'),'market':c.get('market'),'pick':c.get('selection'),'point':c.get('point'),'odds':c.get('odds'),'edge_pct':c.get('edge_pct'),'books':c.get('books'),'pre_score':c.get('pre_score'),'confidence':c.get('confidence'),'single_source':c.get('single_source')}
        if not top_eligible(c):
            item['role']='WATCHLIST'; item['stake_kr']=0; item['reason']='Ikke stærk nok til top bet.'; watch.append(item); continue
        if any(conflicts(c,t) for t in top):
            item['role']='WATCHLIST'; item['stake_kr']=0; item['reason']='Konflikt: allerede valgt andet spil i samme kamp.'; watch.append(item); continue
        ok,why=risk_accept(c,counts)
        if not ok:
            item['role']='WATCHLIST'; item['stake_kr']=0; item['reason']='Risk governor: '+why; watch.append(item); continue
        item['role']='PRIMARY'; item['stake_kr']=unit_stake(c)
        if c.get('single_source'):
            item['reason']='Forsigtigt fallback-pick fra odds-api.io. Kun én bookmaker, derfor lav confidence og 1 unit.'
        else:
            item['reason']=f"Market-consensus pick: score {c.get('pre_score')}, edge {c.get('edge_pct')}%, books {c.get('books')}."
        top.append(item)
        b=sport_bucket(c.get('sport')); counts['sport'][b]=counts['sport'].get(b,0)+1
        if float(c.get('odds') or 0)>=4: counts['longshot']+=1
        if c.get('single_source'): counts['single_source']+=1
        if len(top)>=MAX_TOP_BETS: break
    DIAG['top_count']=len(top)
    return {'summary': ('ingen spil nu' if not top else f'{len(top)} top bets'), 'top_bets': top, 'watchlist': watch[:80], 'pass': [], 'risk_counts': counts}

cands=collect_candidates()
res=rank(cands)
if DIAG.get('quota_exhausted'):
    res['summary']='THE_ODDS_API quota brugt. '+res['summary']+' (odds-api.io fallback aktiv)'
res['mode']=MODE
res['generated_at']=now_iso()
res['candidate_count']=len(cands)
res['diagnostics']=DIAG
res['top_bet_governor']={'max_top_bets':MAX_TOP_BETS,'sport_caps':SPORT_CAPS,'max_longshot_top':MAX_LONGSHOT_TOP,'max_low_conf_top':MAX_LOW_CONF_TOP,'display_tz':DISPLAY_TZ}
(OUT/'v6_expansion_engine.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'v6_expansion_engine.md','w',encoding='utf-8') as f:
    f.write(f"# {MODE}\n\n{res['summary']}\n\n")
    f.write('## DIAGNOSTICS\n```json\n'+json.dumps(DIAG,ensure_ascii=False,indent=2)+'\n```\n\n')
    for sec in ['top_bets','watchlist','pass']:
        f.write('## '+sec.upper()+'\n')
        for i,x in enumerate(as_list(res.get(sec)),1):
            f.write(f"{i}. {x.get('start_local')} | {x.get('event')} | {x.get('market')} | {x.get('pick')} {x.get('point')} | odds {x.get('odds')} | units {x.get('stake_kr')} | source {x.get('source')} | conf {x.get('confidence')} | score {x.get('pre_score')} | {x.get('reason')}\n")
        f.write('\n')
print(res['summary'])
