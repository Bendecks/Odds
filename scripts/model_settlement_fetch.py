import json,os,pathlib,urllib.parse,urllib.request
from datetime import datetime,timezone
SIGNALS=pathlib.Path('data/model_signals.jsonl');SETTLED=pathlib.Path('data/model_settlements.jsonl');QUEUE=pathlib.Path('data/settlement_queue.json');BASE='https://api.odds-api.io/v3'
def load_jsonl(path):
 out=[]
 if path.exists():
  for line in path.read_text().splitlines():
   try:out.append(json.loads(line))
   except Exception:pass
 return out
def write_jsonl(path,rows):path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
def norm(v):return ' '.join(str(v or '').lower().replace('-',' ').split())
def split_event(v):
 s=str(v or '')
 if ' vs ' in s:return s.split(' vs ',1)
 return None,None
def numeric_pair(home,away):
 try:return float(home),float(away)
 except Exception:return None
def integer_score_pair(pair):
 if not pair:return None
 h,a=pair
 if h<0 or a<0 or not h.is_integer() or not a.is_integer():return None
 return int(h),int(a)
def regulation_score_pair(event):
 scores=event.get('scores') or {};periods=scores.get('periods') if isinstance(scores,dict) else None
 if isinstance(periods,dict):
  for key in ('ft','full_time','fulltime','regular_time','regulation'):
   p=periods.get(key)
   if isinstance(p,dict):
    pair=integer_score_pair(numeric_pair(p.get('home'),p.get('away')))
    if pair:return pair
 return None
def has_extra_time_markers(event):
 scores=event.get('scores') or {};periods=scores.get('periods') if isinstance(scores,dict) else None
 if isinstance(periods,dict) and any(k in periods for k in ('et','extra_time','aet','penalties','pens')):return True
 text=' '.join(str(event.get(k) or '') for k in ('status','result','score','note')).lower()
 return any(x in text for x in ('after extra time','aet','penalt','extra time'))
def score_pair(event):
 pair=regulation_score_pair(event)
 if pair:return pair
 if has_extra_time_markers(event):return None
 scores=event.get('scores') or {}
 if isinstance(scores,dict):
  pair=integer_score_pair(numeric_pair(scores.get('home'),scores.get('away')))
  if pair:return pair
 return integer_score_pair(numeric_pair(event.get('home_score'),event.get('away_score')))
def settlement_score_pair(event):
 pair=regulation_score_pair(event)
 if pair:return pair,'regulation_ft'
 if has_extra_time_markers(event):return None,'ambiguous_knockout_score'
 pair=score_pair(event)
 return (pair,'top_level_score') if pair else (None,'missing_score')
def event_payload(data):
 if isinstance(data,dict) and isinstance(data.get('event'),dict):return data['event']
 return data if isinstance(data,dict) else {}
def exact_goal_pick(row):
 raw=row.get('line') if row.get('line') is not None else row.get('pick')
 try:
  value=float(raw)
  return int(value) if value.is_integer() and value>=0 else None
 except Exception:return None
def market_outcome(row,pair):
 pair=integer_score_pair(tuple(float(x) for x in pair)) if pair else None
 if not pair:return None
 h,a=pair;market=str(row.get('market') or '').lower();home,away=split_event(row.get('event'));pick=norm(row.get('pick'))
 if not home:return None
 if market in ('h2h','ml','1x2'):
  winner='draw' if h==a else 'home' if h>a else 'away';field='home' if pick==norm(home) else 'away' if pick==norm(away) else 'draw' if pick in ('draw','uafgjort') else None
  if not field:return None
  return 'win' if field==winner else 'loss'
 if market in ('draw_no_bet','draw no bet','dnb'):
  side='home' if pick==norm(home) else 'away' if pick==norm(away) else None
  if not side:return None
  if h==a:return 'push'
  winner='home' if h>a else 'away'
  return 'win' if side==winner else 'loss'
 if market in ('totals','total'):
  try:line=float(row.get('line'))
  except Exception:return None
  goals=h+a
  if goals==line:return 'push'
  if pick=='over':return 'win' if goals>line else 'loss'
  if pick=='under':return 'win' if goals<line else 'loss'
  return None
 if market in ('total_goals','total goals'):
  try:line=float(row.get('line'))
  except Exception:return None
  if line<=0 or abs((line%1)-0.5)>1e-9:return None
  goals=h+a
  if pick=='over':return 'win' if goals>line else 'loss'
  if pick=='under':return 'win' if goals<line else 'loss'
  return None
 if market in ('team_total_goals_home','team total goals home','team_total_goals_away','team total goals away'):
  try:line=float(row.get('line'))
  except Exception:return None
  if line<=0 or abs((line%1)-0.5)>1e-9:return None
  goals=h if market in ('team_total_goals_home','team total goals home') else a
  if pick=='over':return 'win' if goals>line else 'loss'
  if pick=='under':return 'win' if goals<line else 'loss'
  return None
 if market in ('btts','both teams to score','teams to score'):
  yes=h>0 and a>0
  if pick in ('yes','ja'):return 'win' if yes else 'loss'
  if pick in ('no','nej'):return 'loss' if yes else 'win'
  return None
 if market in ('odd_even','odd/even'):
  wanted='odd' if (h+a)%2 else 'even'
  return 'win' if pick==wanted else 'loss' if pick in ('odd','even') else None
 if market in ('clean_sheet_home','clean sheet home'):
  yes=a==0
  if pick in ('yes','ja'):return 'win' if yes else 'loss'
  if pick in ('no','nej'):return 'loss' if yes else 'win'
  return None
 if market in ('clean_sheet_away','clean sheet away'):
  yes=h==0
  if pick in ('yes','ja'):return 'win' if yes else 'loss'
  if pick in ('no','nej'):return 'loss' if yes else 'win'
  return None
 if market in ('exact_total_goals','exact total goals','home_exact_goals','home team exact goals','away_exact_goals','away team exact goals'):
  wanted=exact_goal_pick(row)
  if wanted is None:return None
  actual=h+a if market in ('exact_total_goals','exact total goals') else h if market in ('home_exact_goals','home team exact goals') else a
  return 'win' if actual==wanted else 'loss'
 if market in ('spreads','spread'):
  try:line=float(row.get('line'))
  except Exception:return None
  side='home' if pick==norm(home) else 'away' if pick==norm(away) else None
  if not side:return None
  margin=(h+line)-a if side=='home' else (a+line)-h
  if margin==0:return 'push'
  return 'win' if margin>0 else 'loss'
 return None
def outcome(row,event):
 event=event_payload(event);status=str(event.get('status') or '').lower()
 if status in ('cancelled','canceled','void','postponed'):return 'void'
 if status not in ('settled','finished','completed','ended'):return None
 pair,_=settlement_score_pair(event)
 return market_outcome(row,pair) if pair else None
def fetch_event(key,event_id):
 url=BASE+'/events?'+urllib.parse.urlencode({'apiKey':key,'eventId':event_id})
 with urllib.request.urlopen(url,timeout=20) as r:return json.load(r)
def main():
 key=os.getenv('ODDS_API_IO_KEY','').strip();signals=load_jsonl(SIGNALS);settled=load_jsonl(SETTLED);done={x.get('signal_id') for x in settled};pending=[x for x in signals if x.get('signal_id') not in done and x.get('bet365_event_id')]
 if not key:
  QUEUE.write_text(json.dumps({'pending':len(pending),'reason':'ODDS_API_IO_KEY missing'},indent=2)+'\n');return
 cache={};added=[];errors=[]
 for row in pending:
  eid=str(row['bet365_event_id'])
  try:
   if eid not in cache:cache[eid]=fetch_event(key,eid)
   event=event_payload(cache[eid]);pair,score_source=settlement_score_pair(event);result=outcome(row,event)
   if result:
    added.append({**row,'outcome':result,'settled_at':datetime.now(timezone.utc).isoformat(),'score_source':score_source,'settlement_score':list(pair) if pair else None})
  except Exception as e:errors.append({'event_id':eid,'error':str(e)[:200]})
 if added:write_jsonl(SETTLED,settled+added)
 QUEUE.write_text(json.dumps({'pending':len(pending)-len(added),'settled_now':len(added),'errors':errors[:20]},indent=2)+'\n')
 print(json.dumps({'pending_before':len(pending),'settled_now':len(added),'errors':len(errors)}))
if __name__=='__main__':main()
