import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone

BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
MODEL='gemini-2.5-flash'
MAX_HOURS=72
MODE='V4_MARKET_ENGINE'
SPORTS=('tennis_atp','tennis_wta','basketball_nba','icehockey_nhl','soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga','soccer_italy_serie_a','soccer_uefa_champs_league','soccer_denmark_superliga')

def ok_sport(k): return any(k.startswith(p) for p in SPORTS)
def get_json(url,params=None):
    r=requests.get(url,params=params or {},timeout=60); r.raise_for_status(); return r.json()
def upcoming(g):
    try:
        t=datetime.fromisoformat(g.get('commence_time','').replace('Z','+00:00'))
        h=(t-datetime.now(timezone.utc)).total_seconds()/3600
        return 0<h<=MAX_HOURS
    except Exception: return False

def implied(o): return 1/o if o and o>1 else 0

def consensus(prices):
    if len(prices)<4: return None
    prices=sorted(prices)
    med=statistics.median(prices)
    avg=statistics.mean(prices)
    best=max(prices)
    spread=best/med if med else 99
    if spread>1.35: return None
    return {'best':best,'median':med,'avg':avg,'spread_ratio':spread,'books':len(prices)}

def risk_stake(odds,edge,books):
    if odds>=4: return 1
    if odds>=3.5: return 1 if edge<0.08 else 2
    if odds>=3: return 1 if edge<0.06 else 2
    if books>=10 and edge>=0.05: return 3
    return 1

def build_market():
    if not ODDS: return []
    raw=get_json('https://api.the-odds-api.com/v4/sports/upcoming/odds',{'apiKey':ODDS,'regions':'eu,uk','markets':'h2h','oddsFormat':'decimal'})
    candidates=[]
    for g in raw:
        sk=g.get('sport_key','')
        if not ok_sport(sk) or not upcoming(g): continue
        by_sel={}
        for b in g.get('bookmakers',[]):
            for m in b.get('markets',[]):
                if m.get('key')!='h2h': continue
                names=[o.get('name','').lower() for o in m.get('outcomes',[])]
                if sk.startswith('icehockey_') and 'draw' in names: continue
                for o in m.get('outcomes',[]):
                    name=o.get('name','')
                    if name.lower()=='draw': continue
                    try: p=float(o['price'])
                    except Exception: continue
                    if 1.2<=p<=8: by_sel.setdefault(name,[]).append(p)
        for sel,prices in by_sel.items():
            c=consensus(prices)
            if not c: continue
            odds=c['best']; med=c['median']
            if odds<1.35 or odds>4.5: continue
            edge=(odds/med)-1
            if odds>=4 and edge<0.08: continue
            if odds>=3 and edge<0.05: continue
            if odds<3 and edge<0.025: continue
            candidates.append({
                'event':f"{g.get('home_team')} vs {g.get('away_team')}",
                'pick':sel,'odds':round(odds,2),'median':round(med,2),
                'edge_pct':round(edge*100,1),'books':c['books'],'spread_ratio':round(c['spread_ratio'],2),
                'sport':sk,'start':g.get('commence_time'),'suggested_stake_kr':risk_stake(odds,edge,c['books'])
            })
    return sorted(candidates,key=lambda x:(x['edge_pct'],x['books']),reverse=True)[:25]

def gemini_rank(cands):
    if not GEMINI: return {'summary':'Missing GEMINI_API_KEY','top_bets':[],'watchlist':cands[:10],'pass':[]}
    prompt='''Du er Bendix V4 Market Engine. Du får kun kandidater der allerede har bestået markedsfiltre.
Regler: konservativ, singles only, ingen livebetting, ingen parlays. Maks stake 5 kr. Odds >=3.5 maks 2 kr, odds >=4 maks 1 kr. Prioriter sandsynlighed + value + lav variance. Returner dansk JSON only: summary, top_bets, watchlist, pass. Hvert item: event,pick,odds,stake_kr,confidence,reason. Hvis ingen stærke spil: top_bets tom.
Data:\n'''+json.dumps({'candidates':cands},ensure_ascii=False)
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}'
    try:
        r=requests.post(url,json={"contents":[{"parts":[{"text":prompt}]}]},timeout=90); r.raise_for_status()
        txt=r.json()['candidates'][0]['content']['parts'][0]['text']
        m=re.search(r'\{.*\}',txt,re.S)
        if m: return json.loads(m.group(0))
    except Exception as e:
        return {'summary':f'Gemini error: {e}','top_bets':[],'watchlist':cands[:10],'pass':[]}
    return {'summary':'No parse','top_bets':[],'watchlist':cands[:10],'pass':[]}

def sanitize(res):
    clean=[]
    for x in res.get('top_bets',[]):
        try: odds=float(str(x.get('odds')).replace(',','.'))
        except Exception: continue
        try: st=int(float(str(x.get('stake_kr',1)).replace(',','.')))
        except Exception: st=1
        if odds>=4: st=min(st,1)
        elif odds>=3.5: st=min(st,2)
        else: st=min(st,5)
        x['stake_kr']=max(1,st)
        clean.append(x)
    res['top_bets']=clean[:5]
    res['watchlist']=res.get('watchlist',[])[:10]
    res['pass']=res.get('pass',[])[:10]
    return res

cands=build_market()
res=sanitize(gemini_rank(cands))
res['mode']=MODE
res['candidate_count']=len(cands)
(OUT/'v4_market_engine.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'v4_market_engine.md','w',encoding='utf-8') as f:
    f.write('# V4 MARKET ENGINE\n\n'+res.get('summary','')+f"\n\nCandidates: {len(cands)}\n\n")
    for sec in ['top_bets','watchlist','pass']:
        f.write('## '+sec.upper()+'\n')
        for i,x in enumerate(res.get(sec,[]),1):
            f.write(f"{i}. {x.get('event')} | {x.get('pick')} | odds {x.get('odds')} | stake {x.get('stake_kr')} | conf {x.get('confidence')} | {x.get('reason')}\n")
        f.write('\n')
print(res.get('summary','done'))
