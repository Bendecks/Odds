import json, math, pathlib
from derived_btts_model import event_inputs, fit_lambdas, MAX_RMSE, exact_event_identity

CAND=pathlib.Path('data/value_candidates.json')
MARKETS=('odd_even','odd_even_home','odd_even_away','clean_sheet_home','clean_sheet_away','exact_total_goals','home_exact_goals','away_exact_goals','team_total_goals_home','team_total_goals_away','total_goals')
TEAM_TOTAL_HALF_LINES=(0.5,1.5,2.5,3.5,4.5)
TOTAL_HALF_LINES=(0.5,1.5,2.5,3.5,4.5,5.5,6.5)


def exact_goal_probability(lam, goals):
    return math.exp(-lam) * (lam ** goals) / math.factorial(goals)


def poisson_cdf(lam, goals):
    return sum(exact_goal_probability(lam,k) for k in range(goals+1))


def odd_even_probabilities(lam):
    even=(1.0+math.exp(-2.0*lam))/2.0
    return {'odd':1.0-even,'even':even}


def half_line_probabilities(lam, line):
    if line<=0 or abs((line%1)-0.5)>1e-9:
        raise ValueError('total line must be a positive half-line')
    under=poisson_cdf(lam,int(math.floor(line)))
    return {'over':1.0-under,'under':under}


def team_total_half_line_probabilities(lam, line):
    return half_line_probabilities(lam,line)


def goal_market_probabilities(home_lambda, away_lambda):
    total = home_lambda + away_lambda
    return {
        'odd_even': odd_even_probabilities(total),
        'odd_even_home': odd_even_probabilities(home_lambda),
        'odd_even_away': odd_even_probabilities(away_lambda),
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
    common={'event':r.get('event'),'event_id':r.get('event_id'),'sport':r.get('sport'),'commence_time':r.get('commence_time'),'books':books,'reference_quality':'strong' if books>=4 else 'good','discovery_eligible':True,'bookmaker':'DERIVED_REFERENCE_MARKET','bet365_verified':False,'model_version':'market-consensus-v6-poisson-goals','model_inputs':'1x2_consensus+totals_2.5_consensus','poisson_home_lambda':round(lh,3),'poisson_away_lambda':round(la,3),'model_fit_rmse':round(rmse,6),**exact_event_identity(rows)}
    out=[]
    for market,selections in goal_market_probabilities(lh,la).items():
        for pick,p in selections.items():
            if not (0<p<1):continue
            row={**common,'market':market,'pick':pick,'fair_probability':round(p,6),'reference_odds':round(1/p,3)}
            if market in ('exact_total_goals','home_exact_goals','away_exact_goals'):row['line']=int(pick)
            out.append(row)
    for market,lam,lines in (('team_total_goals_home',lh,TEAM_TOTAL_HALF_LINES),('team_total_goals_away',la,TEAM_TOTAL_HALF_LINES),('total_goals',lh+la,TOTAL_HALF_LINES)):
        for line in lines:
            for pick,p in half_line_probabilities(lam,line).items():
                if 0<p<1:out.append({**common,'market':market,'pick':pick,'line':line,'fair_probability':round(p,6),'reference_odds':round(1/p,3),'market_semantics':'binary_half_line_no_push'})
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
