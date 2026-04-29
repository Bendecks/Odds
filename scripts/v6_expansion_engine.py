import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone

BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
MODEL='gemini-2.5-flash'
MODE='V6_EXPANSION_ENGINE'
MAX_HOURS=120
SPORTS=('tennis_atp','tennis_wta','basketball_nba','icehockey_nhl','soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga','soccer_italy_serie_a','soccer_uefa_champs_league','soccer_denmark_superliga','soccer_france_ligue_one','soccer_portugal_primeira_liga')
MARKETS=('h2h','spreads','totals')

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
    variance_penalty=0
    if odds>=5: variance_penalty=2.5
    elif odds>=4: variance_penalty=1.5
    elif odds>=3.5: variance_penalty=0.8
    market_bonus=0.8 if market in ('spreads','totals') else 0
    return round(edge*100 + min(books,20)/5 + market_bonus - variance_penalty,2), edge

def add_candidate(cands,g,market,selection,odds_list,point=None):
    if len(odds_list)<2: return
    best=max(odds_list); med=statistics.median(odds_list)
    if best<1.20 or best>8.0: return
    spread_ratio=best/med if med else 99
    if spread_ratio>1.8: return
    score,edge=score_candidate(best,med,len(odds_list),market)
    if score<1.0: return
    cands.append({
        'event':f"{g.get('home_team')} vs {g.get('away_team')}",
        'sport':g.get('sport_key'),
        'start':g.get('commence_time'),
        'market':market,
        'selection':selection,
        'point':point,
        'odds':round(best,2),
        'median':round(med,2),
        'edge_pct':round(edge*100,1),
        'books':len(odds_list),
        'spread_ratio':round(spread_ratio,2),
        'pre_score':score
    })

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
                    key=(mk,name,point)
                    buckets.setdefault(key,[]).append(price)
        for (mk,name,point),prices in buckets.items():
            add_candidate(cands,g,mk,name,prices,point)
    return sorted(cands,key=lambda x:(x['pre_score'],x['books'],x['edge_pct']),reverse=True)

def gemini_rank(cands):
    if not GEMINI:
        return {'summary':'Missing GEMINI_API_KEY','top_bets':[],'watchlist':cands[:30],'pass':[]}
    prompt='''Du er Bendix V6 Expansion Engine.
Du får mange præscreenede kandidater. Din opgave er at rangere, ikke kvæle volumen.
Regler:
- Kvalitet over kvantitet, men INGEN hard cap på gode top_bets.
- Singles only, ingen livebetting, ingen parlays.
- Top_bets må gerne være mange, hvis de alle er gode.
- Sorter top_bets bedst først.
- Odds >=4 må kun være top_bets ved meget stærk edge; ellers watchlist.
- Stake konservativt: 1-5 kr. High odds normalt 1 kr.
- Hvert item: event, market, pick, point, odds, stake_kr, confidence, reason.
- Returner dansk JSON only: summary, top_bets, watchlist, pass.
Data:\n'''+json.dumps({'candidate_count':len(cands),'candidates':cands[:120]},ensure_ascii=False)
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}'
    try:
        r=requests.post(url,json={"contents":[{"parts":[{"text":prompt}]}]},timeout=90); r.raise_for_status()
        txt=r.json()['candidates'][0]['content']['parts'][0]['text']
        m=re.search(r'\{.*\}',txt,re.S)
        if m: return json.loads(m.group(0))
    except Exception as e:
        return {'summary':f'Gemini error: {e}','top_bets':[],'watchlist':cands[:30],'pass':[]}
    return {'summary':'No parse','top_bets':[],'watchlist':cands[:30],'pass':[]}

def as_list(v): return v if isinstance(v,list) else []
def sanitize(res):
    if not isinstance(res,dict): res={}
    res['top_bets']=as_list(res.get('top_bets'))
    res['watchlist']=as_list(res.get('watchlist'))
    res['pass']=as_list(res.get('pass'))
    clean=[]
    for x in res['top_bets']:
        if not isinstance(x,dict): continue
        try: odds=float(str(x.get('odds')).replace(',','.'))
        except Exception: continue
        try: st=int(float(str(x.get('stake_kr',1)).replace(',','.')))
        except Exception: st=1
        if odds>=4: st=min(st,1)
        elif odds>=3.5: st=min(st,2)
        else: st=min(st,5)
        x['stake_kr']=max(1,st)
        clean.append(x)
    res['top_bets']=clean
    res['watchlist']=[x for x in res['watchlist'] if isinstance(x,dict)][:50]
    res['pass']=[x for x in res['pass'] if isinstance(x,dict)][:50]
    res['summary']=res.get('summary') or ('ingen spil nu' if not clean else f'{len(clean)} top bets')
    return res

cands=collect_candidates()
res=sanitize(gemini_rank(cands))
res['mode']=MODE; res['candidate_count']=len(cands)
(OUT/'v6_expansion_engine.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'v6_expansion_engine.md','w',encoding='utf-8') as f:
    f.write('# V6 EXPANSION ENGINE\n\n'+res.get('summary','')+f"\n\nCandidates scanned: {len(cands)}\n\n")
    for sec in ['top_bets','watchlist','pass']:
        f.write('## '+sec.upper()+'\n')
        for i,x in enumerate(as_list(res.get(sec)),1):
            f.write(f"{i}. {x.get('event')} | {x.get('market')} | {x.get('pick')} | {x.get('point')} | odds {x.get('odds')} | stake {x.get('stake_kr')} | conf {x.get('confidence')} | {x.get('reason')}\n")
        f.write('\n')
print(res.get('summary','done'))
