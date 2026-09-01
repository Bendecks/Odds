import json, math, pathlib
from derived_btts_model import event_inputs, fit_lambdas, MAX_RMSE

CAND=pathlib.Path('data/value_candidates.json')
MARKETS=('odd_even','clean_sheet_home','clean_sheet_away','exact_total_goals','home_exact_goals','away_exact_goals')


def exact_goal_probability(lam, goals):
    return math.exp(-lam) * (lam ** goals) / math.factorial(goals)


def goal_market_probabilities(home_lambda, away_lambda):
    total = home_lambda + away_lambda
    even = (1.0 + math.exp(-2.0 * total)) / 2.0
    return {
        'odd_even': {'odd': 1.0 - even, 'even': even},
        'clean_sheet_home': {'yes': math.exp(-away_lambda), 'no': 1.0 - math.exp(-away_lambda)},
        'clean_sheet_away': {'yes': math.exp(-home_lambda), 'no': 1.0 - math.exp(-home_lambda)},
        'exact_total_goals': {str(k): exact_goal_probability(total, k) for k in range(7)},
        'home_exact_goals': {str(k): exact_goal_probability(home_lambda, k) for k in range(5)},
        'away_exact_goals': {str(k): exact_goal_probability(away_lambda, k) for k in range(5)},
    }


def derive_for_event(rows):
    inputs=event_inputs(rows)
    if not inputs:return []
    base,targets=inputs;fit=fit_lambdas(targets)
    if not fit:return []
    mse,lh,la,_=fit;rmse=math.sqrt(mse)
    if rmse>MAX_RMSE:return []
    books=min(int(r.get('books') or 0) for r in base);r=base[0]
    common={'event':r.get('event'),'event_id':r.get('event_id'),'sport':r.get('sport'),'commence_time':r.get('commence_time'),'books':books,'reference_quality':'strong' if books>=4 else 'good','discovery_eligible':True,'bookmaker':'DERIVED_REFERENCE_MARKET','bet365_verified':False,'model_version':'market-consensus-v6-poisson-goals','model_inputs':'1x2_consensus+totals_2.5_consensus','poisson_home_lambda':round(lh,3),'poisson_away_lambda':round(la,3),'model_fit_rmse':round(rmse,6)}
    out=[]
    for market,selections in goal_market_probabilities(lh,la).items():
        for pick,p in selections.items():
            if not (0<p<1):continue
            row={**common,'market':market,'pick':pick,'fair_probability':round(p,6),'reference_odds':round(1/p,3)}
            if market in ('exact_total_goals','home_exact_goals','away_exact_goals'):row['line']=int(pick)
            out.append(row)
    return out


def main():
    candidates=json.loads(CAND.read_text()) if CAND.exists() else [];grouped={}
    for row in candidates:
        if row.get('market') not in ('double_chance','draw_no_bet','btts',*MARKETS):grouped.setdefault(str(row.get('event_id') or ''),[]).append(row)
    derived=[]
    for rows in grouped.values():derived.extend(derive_for_event(rows))
    candidates=[r for r in candidates if r.get('market') not in MARKETS]+derived
    CAND.write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n')
    counts={m:sum(r.get('market')==m for r in derived) for m in MARKETS}
    print(json.dumps({'derived_goal_market_candidates':len(derived),'markets':counts},ensure_ascii=False))

if __name__=='__main__':main()
