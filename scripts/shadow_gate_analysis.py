import json,math,pathlib
from collections import Counter
from datetime import datetime,timezone
import operational_status as ops
import value_decision_engine as engine

CAND=pathlib.Path('data/value_candidates.json')
OUT=pathlib.Path('output/shadow_gate_analysis.json')
STATUS=pathlib.Path('output/operational_status.json')
SCENARIOS=(
 ('production',0.02,0.025,3,20),
 ('very_mild',0.015,0.02,3,20),
 ('mild',0.01,0.015,3,30),
 ('paper_data',0.005,0.01,3,60),
 ('nonnegative_two_books',0.0,0.0,2,60),
)

def analysis_time():
 try:
  status=json.loads(STATUS.read_text());stamp=ops.parse_dt(status.get('generated_at'))
  if stamp:return stamp
 except Exception:pass
 return datetime.now(timezone.utc)

def _evaluate_with_reason(c,now,min_edge,min_ev,min_books,max_age):
 if not ops.exact_identity(c):return None,'identity'
 stamp=ops.parse_dt(c.get('bet365_timestamp'));start=ops.parse_dt(c.get('commence_time'))
 if not stamp:return None,'missing_price_time'
 if not start:return None,'missing_start_time'
 if start<=now:return None,'started'
 age=(now-stamp).total_seconds()/60
 if age<0:return None,'future_price'
 if age>max_age:return None,'stale_price'
 try:odds=float(c.get('bet365_odds',0));p=float(c['fair_probability']);books=int(c.get('books',0))
 except Exception:return None,'invalid_probability_or_odds'
 if odds<=1 or not 0<p<1:return None,'invalid_probability_or_odds'
 implied=1/odds;market=str(c.get('market') or '').lower()
 if market=='draw_no_bet':
  try:pw=float(c['win_probability']);pl=float(c['loss_probability']);pp=float(c.get('push_probability',1-pw-pl))
  except Exception:return None,'invalid_dnb_probabilities'
  if min(pw,pl,pp)<0 or abs(pw+pl+pp-1)>0.01 or pw+pl<=0:return None,'invalid_dnb_probabilities'
  q=pw/(pw+pl);edge=q-implied;ev=pw*(odds-1)-pl;full=max(0.0,(odds*q-1)/(odds-1))
 else:
  edge=p-implied;ev=p*odds-1;full=max(0.0,(odds*p-1)/(odds-1))
 stake=min(engine.BANKROLL*engine.MAX_STAKE_PCT,engine.BANKROLL*full*engine.KELLY_FRACTION);stake=math.floor(stake*2)/2
 row={**c,'edge':edge,'ev':ev,'stake':stake,'score':ev*max(edge,0),'gate_eligible':books>=min_books and edge>=min_edge and ev>=min_ev,'stake_eligible':books>=min_books and edge>=min_edge and ev>=min_ev and stake>=engine.MIN_STAKE}
 if books<min_books:return row,'reference_depth'
 if edge<min_edge:return row,'edge'
 if ev<min_ev:return row,'ev'
 if stake<engine.MIN_STAKE:return row,'stake'
 return row,'eligible'

def evaluate(c,now,min_edge,min_ev,min_books,max_age):
 return _evaluate_with_reason(c,now,min_edge,min_ev,min_books,max_age)[0]

def select(rows):
 ranked=sorted((r for r in rows if r['stake_eligible']),key=lambda r:r['score'],reverse=True);seen={};picks=[]
 per_event=max(1,int(engine.P.get('max_bets_per_event',1)));limit=max(1,int(engine.P.get('max_picks_per_run',25)))
 for row in ranked:
  ek=str(row.get('bet365_event_id') or row.get('event_id') or row.get('event'))
  if seen.get(ek,0)>=per_event:continue
  seen[ek]=seen.get(ek,0)+1;picks.append(row)
  if len(picks)>=limit:break
 return picks

def main():
 now=analysis_time()
 try:candidates=json.loads(CAND.read_text())
 except Exception:candidates=[]
 scenarios=[]
 for name,min_edge,min_ev,min_books,max_age in SCENARIOS:
  evaluated=[_evaluate_with_reason(c,now,min_edge,min_ev,min_books,max_age) for c in candidates]
  rows=[row for row,_ in evaluated if row]
  reasons=Counter(reason for _,reason in evaluated)
  gate=[r for r in rows if r['gate_eligible']];stake=[r for r in rows if r['stake_eligible']];picks=select(rows)
  scenarios.append({'name':name,'min_edge':min_edge,'min_ev':min_ev,'min_reference_books':min_books,'max_price_age_minutes':max_age,'gate_signals':len(gate),'stake_eligible':len(stake),'shadow_paper_picks':len(picks),'unique_events':len({r.get('bet365_event_id') for r in picks if r.get('bet365_event_id')}),'by_market':dict(sorted({m:sum(1 for r in picks if r.get('market')==m) for m in {r.get('market') for r in picks}}.items())),'rejection_reasons':dict(sorted((k,v) for k,v in reasons.items() if k!='eligible'))})
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'as_of':now.isoformat(),'candidate_rows':len(candidates),'note':'Diagnostic only. Simulates start-time, stake, per-event and per-run PAPER gates without changing production policy.','scenarios':scenarios}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
