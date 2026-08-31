import json, math, pathlib, sys
from datetime import datetime, timezone

POLICY_PATH=pathlib.Path('config/value_policy.json')
DEFAULT={'mode':'PAPER','bankroll_dkk':50.0,'min_edge':0.02,'min_ev':0.025,'kelly_fraction':0.125,'max_stake_pct':0.03,'min_stake_dkk':1.0,'max_price_age_minutes':20,'min_reference_books_for_play':3}

def policy():
    try:return {**DEFAULT,**json.loads(POLICY_PATH.read_text())}
    except Exception:return dict(DEFAULT)
P=policy(); BANKROLL=float(P['bankroll_dkk']); MIN_EDGE=float(P['min_edge']); MIN_EV=float(P['min_ev']); KELLY_FRACTION=float(P['kelly_fraction']); MAX_STAKE_PCT=float(P['max_stake_pct']); MIN_STAKE=float(P['min_stake_dkk'])

def parse_dt(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None

def minimum_odds(p):
    if p<=MIN_EDGE or KELLY_FRACTION<=0 or BANKROLL*MAX_STAKE_PCT<MIN_STAKE:return float('inf')
    gates=[(1+MIN_EV)/p,1/(p-MIN_EDGE)]; k=MIN_STAKE/(BANKROLL*KELLY_FRACTION)
    if p<=k:return float('inf')
    gates.append((1-k)/(p-k)); return max(gates)

def evaluate(c, now=None):
    if not c.get('bet365_verified',False): return None
    now=now or datetime.now(timezone.utc); stamp=parse_dt(c.get('bet365_timestamp'))
    if not stamp or (now-stamp).total_seconds()<0 or (now-stamp).total_seconds()>float(P['max_price_age_minutes'])*60:return None
    start=parse_dt(c.get('commence_time'))
    if not start or start<=now:return None
    try: odds=float(c.get('bet365_odds',0)); p=float(c['fair_probability']); books=int(c.get('books',0))
    except Exception:return None
    if odds<=1 or not 0<p<1:return None
    implied=1/odds; edge=p-implied; ev=p*odds-1; full=max(0.0,(odds*p-1)/(odds-1))
    stake=min(BANKROLL*MAX_STAKE_PCT,BANKROLL*full*KELLY_FRACTION); stake=math.floor(stake*2)/2
    enough_reference=books>=int(P.get('min_reference_books_for_play',3))
    qualified=enough_reference and edge>=MIN_EDGE and ev>=MIN_EV and stake>=MIN_STAKE
    mo=minimum_odds(p)
    return {**c,'odds':odds,'implied_probability':round(implied,5),'edge':round(edge,5),'ev':round(ev,5),'stake':stake,'minimum_odds':round(mo,2) if math.isfinite(mo) else None,'enough_reference_for_play':enough_reference,'qualified':qualified,'score':round(ev*max(edge,0),6)}

def decide(candidates, now=None):
    ranked=[x for x in (evaluate(c,now) for c in candidates) if x and x['qualified']]; ranked.sort(key=lambda x:x['score'],reverse=True)
    mode=str(P.get('mode','PAPER')).upper()
    if not ranked:return {'decision':'NO BET','mode':mode,'bankroll':BANKROLL,'reason':'Ingen frisk verificeret Bet365-pris passerer reference-, edge-, EV- og indsatskrav.'}
    x=ranked[0]; action='PLAY' if mode=='LIVE' else 'PAPER PICK'
    return {'decision':action,'mode':mode,'bankroll':BANKROLL,'event':x['event'],'event_id':x.get('event_id'),'sport':x.get('sport'),'market':x.get('market','h2h'),'pick':x['pick'],'bookmaker':'Bet365','odds':x['odds'],'minimum_odds':x['minimum_odds'],'stake':x['stake'],'fair_probability':x['fair_probability'],'reference_books':x.get('books'),'reference_quality':x.get('reference_quality'),'edge':x['edge'],'ev':x['ev'],'model_version':x.get('model_version','unknown'),'price_timestamp':x.get('bet365_timestamp'),'commence_time':x.get('commence_time'),'bet365_event_id':x.get('bet365_event_id'),'event_match_method':x.get('event_match_method') or ('exact' if x.get('bet365_verified') and x.get('bet365_event_id') else None)}

def main():
    src=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'data/value_candidates.json'); out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'output/latest_decision.json')
    try:candidates=json.loads(src.read_text()) if src.exists() else []
    except Exception:candidates=[]
    result=decide(candidates); out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
