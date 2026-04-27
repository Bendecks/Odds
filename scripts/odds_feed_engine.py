import os, json, pathlib, requests, statistics
from datetime import datetime, timezone
BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
API_KEY=os.getenv('THE_ODDS_API_KEY','')
MODE='SMART_ENGINE_V1'
SPORTS=['tennis_atp','tennis_wta','basketball_nba','icehockey_nhl','soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga','soccer_italy_serie_a','soccer_uefa_champs_league','soccer_denmark_superliga']
results=[]; summary='ingen picks'
def ok(k): return any(k.startswith(p) for p in SPORTS)
def dt(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
def novig(pr):
 imp={k:1/v for k,v in pr.items() if v>1}; t=sum(imp.values()); return {k:imp[k]/t for k in imp} if t else {}
def stake(c): return 5 if c>=8.5 else 4 if c>=7.5 else 3 if c>=6.5 else 2 if c>=5.5 else 1
if API_KEY:
 try:
  r=requests.get('https://api.the-odds-api.com/v4/sports/upcoming/odds',params={'apiKey':API_KEY,'regions':'eu,uk','markets':'h2h','oddsFormat':'decimal'},timeout=60)
  r.raise_for_status(); data=r.json(); now=datetime.now(timezone.utc)
  for g in data:
   sk=g.get('sport_key','')
   if not ok(sk): continue
   try: start=dt(g['commence_time'])
   except: continue
   hrs=(start-now).total_seconds()/3600
   if hrs<=0 or hrs>120: continue
   books=g.get('bookmakers',[])
   if len(books)<3: continue
   event=f"{g.get('home_team')} vs {g.get('away_team')}"
   mp={}
   for b in books:
    for m in b.get('markets',[]):
     if m.get('key')!='h2h': continue
     for o in m.get('outcomes',[]):
      try: p=float(o['price'])
      except: continue
      mp.setdefault(o['name'],[]).append(p)
   meds={k:statistics.median(v) for k,v in mp.items() if len(v)>=3}
   probs=novig(meds); cands=[]
   for sel,arr in mp.items():
    if sel.lower()=='draw' or len(arr)<3: continue
    best=max(arr); med=statistics.median(arr)
    if best<1.35 or best>4.5: continue
    edge=(best/med)-1; val=probs.get(sel,0)-(1/best)
    if edge<0.025 or val<0.004: continue
    conf=min(9.5,5+edge*20+val*40+(len(arr)/20))
    cands.append({'selection':sel,'odds':round(best,2),'edge_pct':round(edge*100,1),'value_pct':round(val*100,1),'confidence':round(conf,1),'stake_kr':stake(conf)})
   if cands:
    p=sorted(cands,key=lambda x:(x['confidence'],x['value_pct'],x['edge_pct']),reverse=True)[0]
    p.update({'event':event,'sport':sk,'start':g['commence_time']}); results.append(p)
  results=sorted(results,key=lambda x:(x['confidence'],x['stake_kr'],x['value_pct']),reverse=True)[:12]
  summary=f'{len(results)} prioriterede picks fundet' if results else 'ingen kvalificerede picks fundet'
 except Exception as e:
  summary=f'Feed error: {e}'
else:
 summary='Missing THE_ODDS_API_KEY'
out={'mode':MODE,'summary':summary,'picks':results}
(OUT/'odds_feed.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'odds_feed.md','w',encoding='utf-8') as f:
 f.write('# SMART ENGINE V1\n\n'+summary+'\n\n')
 for i,p in enumerate(results,1):
  f.write(f"## {i}. {p['event']}\n- Pick: {p['selection']}\n- Odds: {p['odds']}\n- Confidence: {p['confidence']}/10\n- Stake: {p['stake_kr']} kr\n- Edge: {p['edge_pct']}%\n- Value: {p['value_pct']}%\n- Sport: {p['sport']}\n- Start: {p['start']}\n\n")
print(summary)
