import os, json, pathlib, requests, re, statistics
from datetime import datetime, timezone, date

BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
FD=os.getenv('FOOTBALL_DATA_API_KEY','')
MODEL='gemini-2.5-flash'
ALLOWED_PREFIXES=('tennis_atp','tennis_wta','basketball_nba','icehockey_nhl','soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga','soccer_italy_serie_a','soccer_uefa_champs_league','soccer_denmark_superliga')
MAX_HOURS=72
MAX_TOP_ODDS=3.5
MAX_WATCH_ODDS=6.0

def odds_penalty(o):
    if o>=5: return -2.0
    if o>=4: return -1.2
    if o>=3.5: return -0.6
    return 0

def required_edge(o):
    if o>=5: return 0.08
    if o>=4: return 0.06
    if o>=3: return 0.04
    return 0.025

def stake(conf,odds):
    base=5 if conf>=8.5 else 4 if conf>=7.5 else 3 if conf>=6.5 else 2
    if odds>=4: return 1
    if odds>=3.5: return min(base,2)
    return base

def as_list(v): return v if isinstance(v,list) else []
def get_json(url,headers=None,params=None):
    r=requests.get(url,headers=headers or {},params=params or {},timeout=45); r.raise_for_status(); return r.json()
def allowed_sport(sk): return any(sk.startswith(p) for p in ALLOWED_PREFIXES)
def upcoming(g):
    try:
        t=datetime.fromisoformat(g.get('commence_time','').replace('Z','+00:00'))
        hrs=(t-datetime.now(timezone.utc)).total_seconds()/3600
        return 0<hrs<=MAX_HOURS
    except Exception: return False

def build_games():
    games=[]
    if not ODDS: return games
    raw=get_json('https://api.the-odds-api.com/v4/sports/upcoming/odds',params={'apiKey':ODDS,'regions':'eu,uk','markets':'h2h','oddsFormat':'decimal'})
    for g in raw:
        sk=g.get('sport_key','')
        if not allowed_sport(sk) or not upcoming(g): continue
        books=g.get('bookmakers',[])
        if len(books)<3: continue
        prices={}
        for b in books:
            for m in b.get('markets',[]):
                if m.get('key')!='h2h': continue
                names=[o.get('name','').lower() for o in m.get('outcomes',[])]
                if sk.startswith('icehockey_') and 'draw' in names: continue
                for o in m.get('outcomes',[]):
                    if o.get('name','').lower()=='draw': continue
                    try:
                        p=float(o['price']); prices.setdefault(o['name'],[]).append(p)
                    except Exception: pass
        selections=[]
        for name,arr in prices.items():
            if len(arr)<3: continue
            best=max(arr); med=statistics.median(arr); edge=(best/med)-1 if med else 0
            if best>MAX_WATCH_ODDS: continue
            if edge<required_edge(best): continue
            if best>3.5 and edge<0.05: continue
            conf=5+edge*20+(len(arr)/20)+odds_penalty(best)
            selections.append({'team':name,'odds':round(best,2),'median_odds':round(med,2),'edge_pct':round(edge*100,1),'books':len(arr),'confidence':round(conf,1),'stake_kr':stake(conf,best)})
        if selections:
            # only one side per event before Gemini
            best_sel=sorted(selections,key=lambda x:(x['confidence'],x['edge_pct'],x['books']),reverse=True)[0]
            games.append({'event':f"{g.get('home_team')} vs {g.get('away_team')}",'sport':sk,'start':g.get('commence_time'),'selection':best_sel})
    return games[:30]

def get_football_context():
    if not FD: return {}
    try:
        d=date.today().isoformat()
        return get_json('https://api.football-data.org/v4/matches',headers={'X-Auth-Token':FD},params={'dateFrom':d,'dateTo':d})
    except Exception: return {}

def sanitize(result):
    if not isinstance(result,dict): result={}
    for sec in ['top_bets','watchlist','pass']:
        result[sec]=as_list(result.get(sec))
    seen=set(); clean=[]; moved=[]
    for x in result.get('top_bets',[]):
        if not isinstance(x,dict): continue
        event=str(x.get('event','')).strip()
        if not event or event in seen: continue
        seen.add(event)
        try: odds=float(str(x.get('odds')).replace(',','.'))
        except Exception: continue
        if odds>MAX_TOP_ODDS:
            x['stake_kr']=0
            x['reason']=str(x.get('reason',''))+' | Flyttet til watchlist: odds over top_bets grænse.'
            moved.append(x); continue
        try: st=int(float(str(x.get('stake_kr',1)).replace(',','.')))
        except Exception: st=1
        if odds>=3.5: st=min(st,2)
        else: st=min(st,5)
        x['stake_kr']=max(1,st)
        clean.append(x)
    result['top_bets']=clean[:5]
    wl=[]
    for x in moved + result['watchlist']:
        if isinstance(x,dict):
            try:
                o=float(str(x.get('odds',0)).replace(',','.'))
                if o>=4: x['stake_kr']=0
            except Exception: pass
            wl.append(x)
    result['watchlist']=wl[:10]
    result['pass']=[x for x in result['pass'] if isinstance(x,dict)][:10]
    result['summary']=result.get('summary') or ('ingen spil nu' if not clean else 'Top bets fundet')
    return result

def run_gemini(games,football):
    if not GEMINI: return {'summary':'Missing GEMINI','top_bets':[],'watchlist':[],'pass':[]}
    payload={'games':games,'football':football,'v3_rules':{'top_bets_max_odds':MAX_TOP_ODDS,'max_one_pick_per_event':True,'odds>=4':'watchlist only, stake 0','prefer':'lower variance value'}}
    prompt='''Du er Bendix konservative betting-analytiker.
Regler:
- Svar på dansk JSON only: summary, top_bets, watchlist, pass.
- top_bets, watchlist og pass skal altid være arrays, aldrig null.
- Maks ét pick pr kamp/event. Aldrig begge sider i samme kamp.
- top_bets må ikke have odds over 3.5. Odds over 3.5 skal i watchlist eller pass.
- Odds >= 4 skal altid have stake_kr 0 og må ikke være top_bets.
- Maks stake 5 kr.
- Vælg kun spil med value og rimelig risiko. Hvis der ikke er spil: ingen spil nu.
- Hvert item: event,pick,odds,confidence,stake_kr,reason.
Data:\n'''+json.dumps(payload,ensure_ascii=False)[:200000]
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}'
    body={"contents":[{"parts":[{"text":prompt}]}]}
    try:
        r=requests.post(url,json=body,timeout=90); r.raise_for_status()
        txt=r.json()['candidates'][0]['content']['parts'][0]['text']
        m=re.search(r'\{.*\}',txt,re.S)
        if m: return sanitize(json.loads(m.group(0)))
    except Exception as e:
        return {'summary':f'error {e}','top_bets':[],'watchlist':[],'pass':[]}
    return {'summary':'no parse','top_bets':[],'watchlist':[],'pass':[]}

def main():
    result=sanitize(run_gemini(build_games(),get_football_context()))
    (OUT/'data_hunter_v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    with open(OUT/'data_hunter_v2.md','w',encoding='utf-8') as f:
        f.write('# DATA HUNTER V3\n\n'+result.get('summary','')+'\n\n')
        for sec in ['top_bets','watchlist','pass']:
            f.write('## '+sec.upper()+'\n')
            for x in as_list(result.get(sec)):
                f.write(f"- {x.get('event')} | {x.get('pick')} | {x.get('odds')} | stake {x.get('stake_kr')} | {x.get('reason')}\n")
            f.write('\n')
    print(result.get('summary','done'))
if __name__=='__main__': main()
