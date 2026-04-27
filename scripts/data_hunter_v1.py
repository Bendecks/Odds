import os, json, pathlib, requests, re
from datetime import date
BASE=pathlib.Path('.')
OUT=BASE/'output'; OUT.mkdir(exist_ok=True)
GEMINI=os.getenv('GEMINI_API_KEY','')
ODDS=os.getenv('THE_ODDS_API_KEY','')
FD=os.getenv('FOOTBALL_DATA_API_KEY','')
MODEL='gemini-2.5-flash'

def get_json(url,headers=None,params=None):
 r=requests.get(url,headers=headers or {},params=params or {},timeout=45)
 r.raise_for_status(); return r.json()

payload={'odds':{},'football':{},'notes':[]}
try:
 if ODDS:
  payload['odds']=get_json('https://api.the-odds-api.com/v4/sports/upcoming/odds',params={'apiKey':ODDS,'regions':'eu,uk','markets':'h2h','oddsFormat':'decimal'})[:25]
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
 prompt='''You are Bendix betting analyst. Use supplied JSON feeds. Be conservative. No live bets. No parlays. Prefer NHL, NBA, ATP/WTA, top football. Return JSON only with keys summary, top_bets, watchlist, pass. Each list item keys: event,pick,odds,confidence,stake_kr,reason. If no odds available say no bets. Data:\n'''+json.dumps(payload,ensure_ascii=False)[:250000]
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

(OUT/'data_hunter_v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
with open(OUT/'data_hunter_v1.md','w',encoding='utf-8') as f:
 f.write('# DATA HUNTER V1\n\n'+result.get('summary','')+'\n\n')
 for sec,label in [('top_bets','TOP BETS'),('watchlist','WATCHLIST'),('pass','PASS')]:
  f.write('## '+label+'\n')
  for i,x in enumerate(result.get(sec,[]),1):
   f.write(f"{i}. {x.get('event')} | {x.get('pick')} | {x.get('odds')} | stake {x.get('stake_kr')} | conf {x.get('confidence')} | {x.get('reason')}\n")
  f.write('\n')
print(result.get('summary','done'))
