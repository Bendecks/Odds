import os, json, pathlib, requests, re
from datetime import date, datetime, timezone
BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
FD=os.getenv('FOOTBALL_DATA_API_KEY','')
MODEL='gemini-2.5-flash'
ALLOWED_PREFIXES=('tennis_atp','tennis_wta','basketball_nba','icehockey_nhl','soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga','soccer_italy_serie_a','soccer_uefa_champs_league','soccer_denmark_superliga')
BANNED_WORDS=('MLB','NCAA','Argentina','Brazil','Série B','Baseball','Primera División - Argentina')
MAX_STAKE=5
NORMAL_STAKE=2

def get_json(url,headers=None,params=None):
 r=requests.get(url,headers=headers or {},params=params or {},timeout=45)
 r.raise_for_status(); return r.json()

def safe_event(g):
 sk=g.get('sport_key','')
 return any(sk.startswith(p) for p in ALLOWED_PREFIXES)

def not_started(g):
 try:
  start=datetime.fromisoformat(g.get('commence_time','').replace('Z','+00:00'))
  return start>datetime.now(timezone.utc)
 except Exception:
  return False

def sanitize(result):
 clean=[]
 for x in result.get('top_bets',[]):
  text=' '.join(str(x.get(k,'')) for k in ['event','pick','reason'])
  if any(w.lower() in text.lower() for w in BANNED_WORDS):
   continue
  try: odds=float(str(x.get('odds')).replace(',','.'))
  except Exception: continue
  if odds<1.25 or odds>4.5: continue
  try: st=int(float(str(x.get('stake_kr',NORMAL_STAKE)).replace(',','.')))
  except Exception: st=NORMAL_STAKE
  x['stake_kr']=max(1,min(st,MAX_STAKE))
  clean.append(x)
 result['top_bets']=clean[:5]
 for sec in ['watchlist','pass']:
  result[sec]=result.get(sec,[])[:10]
 if not result['top_bets']:
  result['summary']='ingen spil nu — Data Hunter fandt ingen sikre kvalificerede picks efter safety-filter.'
 return result

payload={'odds':[], 'football':{}, 'rules':{'max_stake_kr':MAX_STAKE,'normal_stake_kr':NORMAL_STAKE,'allowed_sports':ALLOWED_PREFIXES}, 'notes':[]}
try:
 if ODDS:
  raw=get_json('https://api.the-odds-api.com/v4/sports/upcoming/odds',params={'apiKey':ODDS,'regions':'eu,uk','markets':'h2h','oddsFormat':'decimal'})
  payload['odds']=[g for g in raw if safe_event(g) and not_started(g)][:40]
 else:
  payload['notes'].append('Missing THE_ODDS_API_KEY')
except Exception as e:
 payload['notes'].append(f'odds error {e}')
try:
 if FD:
  d=date.today().isoformat()
  payload['football']=get_json('https://api.football-data.org/v4/matches',headers={'X-Auth-Token':FD},params={'dateFrom':d,'dateTo':d})
 else:
  payload['notes'].append('Missing FOOTBALL_DATA_API_KEY')
except Exception as e:
 payload['notes'].append(f'football error {e}')

result={'summary':'Missing GEMINI_API_KEY','top_bets':[],'watchlist':[],'pass':[]}
if GEMINI:
 prompt='''You are Bendix betting analyst. STRICT SAFETY RULES:
- Conservative bankroll. Max stake 5 kr. Normal stake 1-3 kr.
- No live betting. No parlays. Singles only.
- Allowed sports only: ATP/WTA tennis, NBA, NHL, top European football, Danish Superliga.
- Exclude MLB, NCAA, Argentina, Brazil, obscure leagues, youth/reserve leagues.
- Do not recommend a pick just because it is a favorite. Need explicit value or pass.
- If market is poor, return zero top_bets and say "ingen spil nu".
- Return Danish JSON only with keys summary, top_bets, watchlist, pass.
- Each list item keys: event,pick,odds,confidence,stake_kr,reason.
Data:\n'''+json.dumps(payload,ensure_ascii=False)[:250000]
 url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}'
 body={"contents":[{"parts":[{"text":prompt}]}]}
 try:
  r=requests.post(url,json=body,timeout=90)
  r.raise_for_status()
  txt=r.json()['candidates'][0]['content']['parts'][0]['text']
  m=re.search(r'\{.*\}',txt,re.S)
  if m: result=json.loads(m.group(0))
  else: result={'summary':txt,'top_bets':[],'watchlist':[],'pass':[]}
 except Exception as e:
  result={'summary':f'Gemini error {e}','top_bets':[],'watchlist':[],'pass':[]}
result=sanitize(result)
(OUT/'data_hunter_v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'data_hunter_v1.md','w',encoding='utf-8') as f:
 f.write('# DATA HUNTER V1 — SAFETY FIXED\n\n'+result.get('summary','')+'\n\n')
 for sec,label in [('top_bets','TOP BETS'),('watchlist','WATCHLIST'),('pass','PASS')]:
  f.write('## '+label+'\n')
  for i,x in enumerate(result.get(sec,[]),1):
   f.write(f"{i}. {x.get('event')} | {x.get('pick')} | {x.get('odds')} | stake {x.get('stake_kr')} | conf {x.get('confidence')} | {x.get('reason')}\n")
  f.write('\n')
print(result.get('summary','done'))
