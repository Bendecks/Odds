import json, math, pathlib, sys

BANKROLL = 50.0
MIN_EDGE = 0.02
MIN_EV = 0.025
KELLY_FRACTION = 0.125
MAX_STAKE_PCT = 0.03
MIN_STAKE = 1.0


def evaluate(c):
    odds=float(c['odds']); p=float(c['fair_probability'])
    if odds <= 1 or not 0 < p < 1: return None
    implied=1/odds; edge=p-implied; ev=p*odds-1
    full=max(0.0,(odds*p-1)/(odds-1))
    stake=min(BANKROLL*MAX_STAKE_PCT,BANKROLL*full*KELLY_FRACTION)
    stake=math.floor(stake*2)/2
    qualified=edge>=MIN_EDGE and ev>=MIN_EV and stake>=MIN_STAKE
    return {**c,'implied_probability':round(implied,5),'edge':round(edge,5),'ev':round(ev,5),'stake':stake,'qualified':qualified,'score':round(ev*max(edge,0),6)}


def decide(candidates):
    ranked=[x for x in (evaluate(c) for c in candidates) if x and x['qualified']]
    ranked.sort(key=lambda x:x['score'],reverse=True)
    if not ranked:
        return {'decision':'NO BET','bankroll':BANKROLL,'reason':'No candidate passes edge, EV and stake gates.'}
    x=ranked[0]
    return {'decision':'PLAY','bankroll':BANKROLL,'event':x['event'],'pick':x['pick'],'bookmaker':x.get('bookmaker','Bet365'),'odds':x['odds'],'minimum_odds':x['odds'],'stake':x['stake'],'fair_probability':x['fair_probability'],'edge':x['edge'],'ev':x['ev'],'model_version':x.get('model_version','unknown')}


def main():
    src=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'data/value_candidates.json')
    out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'output/latest_decision.json')
    candidates=json.loads(src.read_text()) if src.exists() else []
    result=decide(candidates); out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__': main()
