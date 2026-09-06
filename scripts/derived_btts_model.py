import json, math, pathlib

CAND=pathlib.Path('data/value_candidates.json')
MIN_BOOKS=3
MAX_RMSE=0.06
MODEL_VERSION='market-consensus-v6-poisson-btts'
DERIVED_PROVENANCE={
    'transport_provider_id':'local-derived-market-model',
    'economic_source_id':'derived:market-consensus-poisson',
    'evidence_family':'derived_probability',
}


def poisson_probs(lam,max_goals=15):
    probs=[math.exp(-lam)]
    for k in range(1,max_goals+1):probs.append(probs[-1]*lam/k)
    return probs


def model_probs(home_lambda,away_lambda):
    ph=poisson_probs(home_lambda);pa=poisson_probs(away_lambda)
    home=draw=away=0.0
    for i,p1 in enumerate(ph):
        for j,p2 in enumerate(pa):
            p=p1*p2
            if i>j:home+=p
            elif i==j:draw+=p
            else:away+=p
    total=home+draw+away
    if total<=0:return None
    home/=total;draw/=total;away/=total
    lam=home_lambda+away_lambda
    over25=1-math.exp(-lam)*(1+lam+lam*lam/2)
    btts=1-math.exp(-home_lambda)-math.exp(-away_lambda)+math.exp(-lam)
    return home,draw,away,over25,btts


def fit_error(home_lambda,away_lambda,targets):
    probs=model_probs(home_lambda,away_lambda)
    if not probs:return None
    return sum((a-b)**2 for a,b in zip(probs[:4],targets))/4,probs


def fit_lambdas(targets):
    best=None
    for hi in range(2,41):
        lh=hi/10
        for ai in range(2,41):
            la=ai/10;result=fit_error(lh,la,targets)
            if not result:continue
            mse,probs=result
            if best is None or mse<best[0]:best=(mse,lh,la,probs[4])
    if not best:return None
    _,bh,ba,_=best
    for hi in range(max(5,int((bh-.15)*100)),int((bh+.15)*100)+1):
        lh=hi/100
        for ai in range(max(5,int((ba-.15)*100)),int((ba+.15)*100)+1):
            la=ai/100;result=fit_error(lh,la,targets)
            if not result:continue
            mse,probs=result
            if mse<best[0]:best=(mse,lh,la,probs[4])
    return best


def event_inputs(rows):
    h2h = [r for r in rows if r.get('market') == 'h2h' and int(r.get('books') or 0) >= MIN_BOOKS]
    totals = [r for r in rows if r.get('market') == 'totals' and r.get('line') == 2.5 and int(r.get('books') or 0) >= MIN_BOOKS]
    if len(h2h) < 3 or len(totals) < 2:return None
    event = str(rows[0].get('event') or '')
    if ' vs ' not in event:return None
    home_name, away_name = event.split(' vs ', 1)
    by_pick = {str(r.get('pick')): r for r in h2h}
    home = by_pick.get(home_name); away = by_pick.get(away_name)
    draw = next((r for r in h2h if str(r.get('pick')).lower() == 'draw'), None)
    over = next((r for r in totals if str(r.get('pick')).lower() == 'over'), None)
    if not all((home, away, draw, over)):return None
    base = [home, draw, away, over]
    try:probs = tuple(float(r['fair_probability']) for r in base)
    except (TypeError, ValueError, KeyError):return None
    if any(p <= 0 or p >= 1 for p in probs):return None
    return base, probs


def exact_event_identity(rows):
    for row in rows:
        if row.get('bet365_event_id') and row.get('event_match_method') == 'exact':
            return {'bet365_event_id':row['bet365_event_id'],'event_match_method':'exact'}
    return {}


def merge_reference_sources(rows, model_version):
    sources=[];seen=set()
    for row in rows:
        for source in row.get('reference_sources') or []:
            if not isinstance(source,dict):continue
            key=str(source.get('economic_source_id') or '').strip().lower()
            if not key or key in seen:continue
            seen.add(key);sources.append(source)
    derived={**DERIVED_PROVENANCE,'model_or_feed_version':model_version}
    key=derived['economic_source_id']
    if key not in seen:sources.append(derived)
    return sources


def derive_for_event(rows):
    inputs = event_inputs(rows)
    if not inputs:return []
    base, targets = inputs; fit = fit_lambdas(targets)
    if not fit:return []
    mse, lh, la, p_yes = fit; rmse = math.sqrt(mse)
    if rmse > MAX_RMSE or not (0 < p_yes < 1):return []
    p_no = 1.0 - p_yes
    books = min(int(r.get('books') or 0) for r in base); r = base[0]
    common = {'event':r.get('event'),'event_id':r.get('event_id'),'sport':r.get('sport'),'commence_time':r.get('commence_time'),'market':'btts','books':books,'reference_quality':'strong' if books >= 4 else 'good','discovery_eligible':True,'bookmaker':'DERIVED_REFERENCE_MARKET','bet365_verified':False,'model_version':MODEL_VERSION,'model_inputs':'1x2_consensus+totals_2.5_consensus','poisson_home_lambda':round(lh,3),'poisson_away_lambda':round(la,3),'model_fit_rmse':round(rmse,6),'reference_sources':merge_reference_sources(base,MODEL_VERSION),**exact_event_identity(rows)}
    return [{**common,'pick':'yes','fair_probability':round(p_yes,6),'reference_odds':round(1/p_yes,3)},{**common,'pick':'no','fair_probability':round(p_no,6),'reference_odds':round(1/p_no,3)}]


def main():
    candidates = json.loads(CAND.read_text()) if CAND.exists() else []; grouped={}
    for row in candidates:
        if row.get('market') not in ('double_chance','draw_no_bet','btts'):grouped.setdefault(str(row.get('event_id') or ''),[]).append(row)
    derived=[]
    for rows in grouped.values():derived.extend(derive_for_event(rows))
    candidates=[r for r in candidates if r.get('market')!='btts']+derived
    CAND.write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'derived_btts_candidates':len(derived),'derived_btts_events':len(derived)//2}))

if __name__=='__main__':main()
