import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone

BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
MODEL='gemini-2.5-flash'
MODE='V6_CORRELATION_RESOLVER'
MAX_HOURS=120
SPORTS=('tennis_atp','tennis_wta','basketball_nba','icehockey_nhl','soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga','soccer_italy_serie_a','soccer_uefa_champs_league','soccer_denmark_superliga','soccer_france_ligue_one','soccer_portugal_primeira_liga')
MARKETS=('h2h','spreads','totals')

def text(v):
    if isinstance(v,str): return v
    if v is None: return ''
    return json.dumps(v,ensure_ascii=False)
def ok_sport(k): return any(k.startswith(p) for p in SPORTS)
def get_json(url,params=None):
    r=requests.get(url,params=params or {},timeout=60); r.raise_for_status(); return r.json()
def upcoming(g):
    try:
        t=datetime.fromisoformat(g.get('commence_time','').replace('Z','+00:00'))
        h=(t-datetime.now(timezone.utc)).total_seconds()/3600
        return 0<h<=MAX_HOURS
    except Exception: return False

def score_candidate(odds,median,books,market):
    edge=(odds/median)-1 if median else 0
    variance_penalty=2.5 if odds>=5 else 1.5 if odds>=4 else 0.8 if odds>=3.5 else 0
    market_bonus=0.8 if market in ('spreads','totals') else 0
    return round(edge*100 + min(books,20)/5 + market_bonus - variance_penalty,2), edge

def conflicts(a,b):
    if a.get('event')!=b.get('event'): return False
    if a.get('market')=='h2h' and b.get('market')=='h2h': return True
    if a.get('market')=='totals' and b.get('market')=='totals' and str(a.get('point'))==str(b.get('point')):
        return str(a.get('selection')).lower()!=str(b.get('selection')).lower()
    if a.get('market')=='spreads' and b.get('market')=='spreads' and str(a.get('point'))==str(b.get('point')):
        return str(a.get('selection')).lower()!=str(b.get('selection')).lower()
    return False

def add_candidate(cands,g,market,selection,odds_list,point=None):
    if len(odds_list)<2: return
    best=max(odds_list); med=statistics.median(odds_list)
    if best<1.20 or best>8.0: return
    spread_ratio=best/med if med else 99
    if spread_ratio>1.8: return
    score,edge=score_candidate(best,med,len(odds_list),market)
    if score<1.0: return
    cands.append({'event':f"{g.get('home_team')} vs {g.get('away_team')}",'sport':g.get('sport_key'),'start':g.get('commence_time'),'market':market,'selection':selection,'point':point,'odds':round(best,2),'median':round(med,2),'edge_pct':round(edge*100,1),'books':len(odds_list),'spread_ratio':round(spread_ratio,2),'pre_score':score})

def collect_candidates():
    if not ODDS: return []
    raw=get_json('https://api.the-odds-api.com/v4/sports/upcoming/odds',{'apiKey':ODDS,'regions':'eu,uk','markets':','.join(MARKETS),'oddsFormat':'decimal'})
    cands=[]
    for g in raw:
        if not ok_sport(g.get('sport_key','')) or not upcoming(g): continue
        buckets={}
        for b in g.get('bookmakers',[]):
            for m in b.get('markets',[]):
                mk=m.get('key')
                if mk not in MARKETS: continue
                outcomes=m.get('outcomes',[])
                names=[o.get('name','').lower() for o in outcomes]
                if g.get('sport_key','').startswith('icehockey_') and mk=='h2h' and 'draw' in names: continue
                for o in outcomes:
                    name=o.get('name','')
                    if name.lower()=='draw': continue
                    try: price=float(o['price'])
                    except Exception: continue
                    point=o.get('point')
                    buckets.setdefault((mk,name,point),[]).append(price)
        for (mk,name,point),prices in buckets.items(): add_candidate(cands,g,mk,name,prices,point)
    return sorted(cands,key=lambda x:(x['pre_score'],x['books'],x['edge_pct']),reverse=True)

def pre_resolve(cands):
    selected=[]; watch=[]
    for c in cands:
        if any(conflicts(c,s) for s in selected):
            watch.append({**c,'conflict_status':'market_conflict'}); continue
        selected.append({**c,'conflict_status':'clear'})
    return selected,watch

def gemini_rank(cands,conflict_watch):
    if not GEMINI: return {'summary':'Missing GEMINI_API_KEY','top_bets':cands[:10],'watchlist':conflict_watch[:20],'pass':[]}
    prompt='''Du er Bendix V6 Correlation Resolver.
Regler:
- Kvalitet over kvantitet, men maks 1 TOP_BET pr event/kamp.
- Øvrige gode picks fra samme kamp skal i watchlist som secondary leans.
- Singles only, ingen livebetting, ingen parlays.
- ALDRIG modsatrettede picks i samme kamp.
- Hvis h2h-underdog vælges, må favorit-spread ikke være top_bet.
- Hvis h2h vælges, må totals fra samme kamp kun være watchlist, ikke top_bet.
- Hvert item: event, market, pick, point, odds, stake_kr, confidence, role, reason.
- role skal være PRIMARY eller WATCHLIST.
- Returner dansk JSON only: summary, top_bets, watchlist, pass.
Data:\n'''+json.dumps({'candidates':cands[:120],'conflict_watchlist':conflict_watch[:50]},ensure_ascii=False)
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}'
    try:
        r=requests.post(url,json={"contents":[{"parts":[{"text":prompt}]}]},timeout=90); r.raise_for_status()
        txt=r.json()['candidates'][0]['content']['parts'][0]['text']
        m=re.search(r'\{.*\}',txt,re.S)
        if m: return json.loads(m.group(0))
    except Exception as e:
        return {'summary':f'Gemini error: {e}','top_bets':cands[:5],'watchlist':conflict_watch[:20],'pass':[]}
    return {'summary':'No parse','top_bets':cands[:5],'watchlist':conflict_watch[:20],'pass':[]}

def as_list(v): return v if isinstance(v,list) else []
def normalize_item(x):
    if not isinstance(x,dict): return None
    if 'selection' in x and 'pick' not in x: x['pick']=x.get('selection')
    return x

def sanitize(res):
    if not isinstance(res,dict): res={}
    for sec in ['top_bets','watchlist','pass']:
        res[sec]=[normalize_item(x) for x in as_list(res.get(sec))]
        res[sec]=[x for x in res[sec] if isinstance(x,dict)]
    clean=[]; seen_events=set(); moved=[]
    for x in res['top_bets']:
        event=x.get('event')
        if event in seen_events:
            x['stake_kr']=0; x['role']='WATCHLIST'; x['reason']=text(x.get('reason'))+' | Flyttet til watchlist: maks 1 top_bet pr kamp.'; moved.append(x); continue
        try: odds=float(str(x.get('odds')).replace(',','.'))
        except Exception: continue
        try: st=int(float(str(x.get('stake_kr',1)).replace(',','.')))
        except Exception: st=1
        if odds>=4: st=min(st,1)
        elif odds>=3.5: st=min(st,2)
        else: st=min(st,5)
        x['stake_kr']=max(1,st); x['role']='PRIMARY'
        item={'event':event,'market':x.get('market'),'selection':x.get('pick'),'point':x.get('point')}
        if any(conflicts(item,{'event':y.get('event'),'market':y.get('market'),'selection':y.get('pick'),'point':y.get('point')}) for y in clean):
            x['stake_kr']=0; x['role']='WATCHLIST'; x['reason']=text(x.get('reason'))+' | Flyttet til watchlist: konflikt.'; moved.append(x); continue
        clean.append(x); seen_events.add(event)
    res['top_bets']=clean
    res['watchlist']=(moved+res['watchlist'])[:50]
    res['pass']=res['pass'][:50]
    summary=res.get('summary')
    res['summary']=summary if isinstance(summary,str) else (json.dumps(summary,ensure_ascii=False) if summary else ('ingen spil nu' if not clean else f'{len(clean)} primary top bets'))
    return res

raw_cands=collect_candidates(); resolved,conflict_watch=pre_resolve(raw_cands); res=sanitize(gemini_rank(resolved,conflict_watch))
res['mode']=MODE; res['candidate_count']=len(raw_cands); res['resolved_count']=len(resolved); res['conflict_watch_count']=len(conflict_watch)
(OUT/'v6_expansion_engine.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'v6_expansion_engine.md','w',encoding='utf-8') as f:
    f.write('# V6 EXPANSION ENGINE — CORRELATION RESOLVER\n\n'+text(res.get('summary'))+f"\n\nCandidates scanned: {len(raw_cands)} | Resolved: {len(resolved)} | Conflict watchlist: {len(conflict_watch)}\n\n")
    for sec in ['top_bets','watchlist','pass']:
        f.write('## '+sec.upper()+'\n')
        for i,x in enumerate(as_list(res.get(sec)),1): f.write(f"{i}. {x.get('event')} | {x.get('market')} | {x.get('pick')} | {x.get('point')} | odds {x.get('odds')} | stake {x.get('stake_kr')} | role {x.get('role')} | conf {x.get('confidence')} | {text(x.get('reason'))}\n")
        f.write('\n')
print(text(res.get('summary')))
