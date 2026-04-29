import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone

BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
MODEL='gemini-2.5-flash'
MODE='V6_TOP_BET_GOVERNOR'
MAX_HOURS=168
MAX_TOP_BETS=12
MIN_TOP_SCORE=14.0
MAX_AUTO_ODDS=6.0
SPORT_PREFIXES=('tennis_','basketball_','icehockey_','soccer_')
SPORT_DENY=('soccer_esports','basketball_esports','tennis_esports')
MARKETS=('h2h','spreads','totals')

def text(v):
    if isinstance(v,str): return v
    if v is None: return ''
    return json.dumps(v,ensure_ascii=False)
def as_list(v): return v if isinstance(v,list) else []
def ok_sport(k): return any(k.startswith(p) for p in SPORT_PREFIXES) and not any(k.startswith(d) for d in SPORT_DENY)
def get_json(url,params=None):
    r=requests.get(url,params=params or {},timeout=60); r.raise_for_status(); return r.json()
def upcoming(g):
    try:
        t=datetime.fromisoformat(g.get('commence_time','').replace('Z','+00:00'))
        h=(t-datetime.now(timezone.utc)).total_seconds()/3600
        return 0<h<=MAX_HOURS
    except Exception: return False

def list_sports():
    if not ODDS: return []
    try:
        sports=get_json('https://api.the-odds-api.com/v4/sports',{'apiKey':ODDS})
        return [s.get('key') for s in sports if s.get('active') and ok_sport(s.get('key',''))]
    except Exception: return []

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
    try:
        odds=float(odds); edge=float(edge_pct); books=int(books or 0); pre=float(pre_score or 0)
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
    try:
        odds=float(c.get('odds')); score=float(c.get('pre_score') or 0); books=int(c.get('books') or 0); edge=float(c.get('edge_pct') or 0)
    except Exception: return False
    if score < MIN_TOP_SCORE: return False
    if odds > MAX_AUTO_ODDS: return False
    if odds >= 4.0 and edge < 12: return False
    if books < 8: return False
    if c.get('market')!='h2h' and books < 10: return False
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
    if len(odds_list)<2: return
    best=max(odds_list); med=statistics.median(odds_list)
    if best<1.20 or best>8.0: return
    spread_ratio=best/med if med else 99
    if spread_ratio>2.0: return
    score,edge,robust=score_candidate(best,med,len(odds_list),market,point)
    if score<0.5: return
    cands.append({'event':f"{g.get('home_team')} vs {g.get('away_team')}",'sport':g.get('sport_key'),'start':g.get('commence_time'),'market':market,'selection':selection,'point':point,'odds':round(best,2),'median':round(med,2),'edge_pct':round(edge*100,1),'books':len(odds_list),'spread_ratio':round(spread_ratio,2),'market_weight':robust,'pre_score':score})

def parse_games(raw):
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
    return cands

def collect_candidates():
    if not ODDS: return []
    all_games=[]
    try: all_games+=get_json('https://api.the-odds-api.com/v4/sports/upcoming/odds',{'apiKey':ODDS,'regions':'eu,uk,us','markets':','.join(MARKETS),'oddsFormat':'decimal'})
    except Exception: pass
    for sk in list_sports()[:80]:
        try: all_games+=get_json(f'https://api.the-odds-api.com/v4/sports/{sk}/odds',{'apiKey':ODDS,'regions':'eu,uk,us','markets':','.join(MARKETS),'oddsFormat':'decimal'})
        except Exception: continue
    seen=set(); uniq=[]
    for g in all_games:
        gid=g.get('id') or (g.get('sport_key'),g.get('commence_time'),g.get('home_team'),g.get('away_team'))
        if str(gid) in seen: continue
        seen.add(str(gid)); uniq.append(g)
    cands=parse_games(uniq)
    return sorted(cands,key=lambda x:(x['pre_score'],x['books'],x['edge_pct']),reverse=True)

def pre_resolve(cands):
    selected=[]; watch=[]
    for c in cands:
        if any(conflicts(c,s) for s in selected): watch.append({**c,'conflict_status':'market_conflict'}); continue
        selected.append({**c,'conflict_status':'clear'})
    return selected,watch

def fallback_rank(cands):
    out=[]; seen=set()
    eligible=[c for c in cands if is_top_eligible(c)]
    for c in eligible:
        if c.get('event') in seen: continue
        out.append({'event':c['event'],'market':c['market'],'pick':c['selection'],'point':c.get('point'),'odds':c['odds'],'confidence':'auto','role':'PRIMARY','reason':f"Auto-valgt af Top Bet Governor: score {c.get('pre_score')}, edge {c.get('edge_pct')}%, books {c.get('books')}."})
        seen.add(c.get('event'))
        if len(out)>=MAX_TOP_BETS: break
    return out

def gemini_rank(cands,conflict_watch):
    shortlist=[c for c in cands if is_top_eligible(c)][:60]
    watch_seed=[c for c in cands if not is_top_eligible(c)][:80]+conflict_watch[:80]
    if not GEMINI: return {'summary':'Missing GEMINI_API_KEY','top_bets':fallback_rank(cands),'watchlist':watch_seed[:80],'pass':[]}
    prompt='''Du er Bendix V6 Top Bet Governor.
Regler:
- Vælg kun de stærkeste top_bets fra shortlist.
- Maks 12 top_bets i output.
- Maks 1 TOP_BET pr event/kamp.
- Høj odds underdogs skal være få og stærke; ellers watchlist.
- H2H med mange bookmakere prioriteres over totals/spreads med få bookmakere.
- Singles only, ingen livebetting, ingen parlays.
- ALDRIG modsatrettede picks i samme kamp.
- Stake overskrives deterministisk af Python bagefter.
- Hvert item: event, market, pick, point, odds, confidence, role, reason.
- Returner dansk JSON only: summary, top_bets, watchlist, pass.
Data:\n'''+json.dumps({'shortlist_count':len(shortlist),'shortlist':shortlist,'watch_seed':watch_seed[:80]},ensure_ascii=False)
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
        for k in ['edge_pct','books','pre_score','median','market_weight','sport','start']:
            item[k]=c.get(k)
    return item

def sanitize(res, all_candidates):
    lookup={(c.get('event'),c.get('market'),str(c.get('selection')),str(c.get('point'))):c for c in all_candidates}
    if not isinstance(res,dict): res={}
    for sec in ['top_bets','watchlist','pass']:
        res[sec]=[normalize_item(x) for x in as_list(res.get(sec))]
        res[sec]=[x for x in res[sec] if isinstance(x,dict)]
    # force governor fallback to avoid Gemini over/under-selecting
    top=res['top_bets']
    if len(top)==0 or len(top)>MAX_TOP_BETS:
        top=fallback_rank(all_candidates)
    clean=[]; seen_events=set(); moved=[]
    for x in top:
        x=apply_candidate_metrics(x,lookup); event=x.get('event')
        try: odds=float(str(x.get('odds')).replace(',','.'))
        except Exception: continue
        c={'event':event,'market':x.get('market'),'selection':x.get('pick'),'point':x.get('point'),'odds':odds,'pre_score':x.get('pre_score'),'books':x.get('books'),'edge_pct':x.get('edge_pct')}
        if event in seen_events or not is_top_eligible(c):
            x['stake_kr']=0; x['role']='WATCHLIST'; x['reason']=text(x.get('reason'))+' | Flyttet til watchlist af Top Bet Governor.'; moved.append(x); continue
        x['role']='PRIMARY'; x['stake_kr']=deterministic_stake(odds,x.get('edge_pct',0),x.get('books',0),x.get('pre_score',0),x.get('market'),'PRIMARY')
        item={'event':event,'market':x.get('market'),'selection':x.get('pick'),'point':x.get('point')}
        if any(conflicts(item,{'event':y.get('event'),'market':y.get('market'),'selection':y.get('pick'),'point':y.get('point')}) for y in clean):
            x['stake_kr']=0; x['role']='WATCHLIST'; x['reason']=text(x.get('reason'))+' | Flyttet til watchlist: konflikt.'; moved.append(x); continue
        clean.append(x); seen_events.add(event)
        if len(clean)>=MAX_TOP_BETS: break
    watch=[]
    for x in moved+res['watchlist']:
        x=apply_candidate_metrics(x,lookup); x['stake_kr']=0; x['role']='WATCHLIST'; watch.append(x)
    for x in res['pass']: x['stake_kr']=0
    res['top_bets']=sorted(clean,key=lambda x:(float(x.get('pre_score') or 0), int(x.get('books') or 0)),reverse=True)
    res['watchlist']=watch[:80]; res['pass']=res['pass'][:80]
    summary=res.get('summary')
    res['summary']=summary if isinstance(summary,str) else (json.dumps(summary,ensure_ascii=False) if summary else ('ingen spil nu' if not clean else f'{len(clean)} primary top bets'))
    return res

raw_cands=collect_candidates(); resolved,conflict_watch=pre_resolve(raw_cands); res=sanitize(gemini_rank(resolved,conflict_watch),raw_cands)
res['mode']=MODE; res['candidate_count']=len(raw_cands); res['resolved_count']=len(resolved); res['conflict_watch_count']=len(conflict_watch)
res['top_bet_governor']={'max_top_bets':MAX_TOP_BETS,'min_top_score':MIN_TOP_SCORE,'max_auto_odds':MAX_AUTO_ODDS}
(OUT/'v6_expansion_engine.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'v6_expansion_engine.md','w',encoding='utf-8') as f:
    f.write('# V6 EXPANSION ENGINE — TOP BET GOVERNOR\n\n'+text(res.get('summary'))+f"\n\nCandidates scanned: {len(raw_cands)} | Resolved: {len(resolved)} | Conflict watchlist: {len(conflict_watch)} | Governor max top bets: {MAX_TOP_BETS}\n\n")
    for sec in ['top_bets','watchlist','pass']:
        f.write('## '+sec.upper()+'\n')
        for i,x in enumerate(as_list(res.get(sec)),1): f.write(f"{i}. {x.get('event')} | {x.get('market')} | {x.get('pick')} | {x.get('point')} | odds {x.get('odds')} | stake {x.get('stake_kr')} | role {x.get('role')} | edge {x.get('edge_pct')} | books {x.get('books')} | market_weight {x.get('market_weight')} | score {x.get('pre_score')} | conf {x.get('confidence')} | {text(x.get('reason'))}\n")
        f.write('\n')
print(text(res.get('summary')))
