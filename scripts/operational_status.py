import json, pathlib
from collections import Counter
from datetime import datetime, timezone

import value_decision_engine as engine

CANDIDATES=pathlib.Path('data/value_candidates.json')
DECISION=pathlib.Path('output/latest_decision.json')
BET365=pathlib.Path('output/bet365_join_status.json')
REFERENCE_DIAG=pathlib.Path('output/reference_match_diagnostics.json')
MARKET_COVERAGE=pathlib.Path('output/market_coverage_report.json')
DECISION_RUNS=pathlib.Path('data/decision_runs.jsonl')
OUT=pathlib.Path('output/operational_status.json')

def load_json(path, default):
    try:return json.loads(path.read_text())
    except Exception:return default

def read_jsonl(path):
    rows=[]
    if not path.exists(): return rows
    for line in path.read_text().splitlines():
        try:rows.append(json.loads(line))
        except Exception:pass
    return rows

def parse_dt(value):
    try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None

def exact_identity(candidate):
    return bool(candidate.get('bet365_verified')) and bool(str(candidate.get('bet365_event_id') or '').strip()) and candidate.get('event_match_method')=='exact'

def fresh_bet365(candidate, now):
    stamp=parse_dt(candidate.get('bet365_timestamp'))
    if not stamp:return False
    age=(now-stamp).total_seconds(); max_age=float(engine.P.get('max_price_age_minutes',20))*60
    return 0 <= age <= max_age

def candidate_edge(candidate):
    try: odds=float(candidate.get('bet365_odds',0)); probability=float(candidate.get('fair_probability'))
    except Exception:return None,None
    if odds<=1 or not 0<probability<1:return None,None
    if str(candidate.get('market') or '').lower()=='draw_no_bet':
        try:pw=float(candidate['win_probability']);pl=float(candidate['loss_probability'])
        except Exception:return None,None
        if pw<0 or pl<0 or pw+pl<=0:return None,None
        return pw/(pw+pl)-(1/odds),pw*(odds-1)-pl
    return probability-(1/odds),probability*odds-1

def provider_available(status):
    if 'provider_available' in status:return status.get('provider_available')
    if 'provider_unavailable' in status:return not bool(status.get('provider_unavailable'))
    return None

def first_present(source,*keys):
    for key in keys:
        if key in source:return source.get(key)
    return None

def market_counts(rows):
    return dict(sorted(Counter(str(c.get('market') or 'unknown') for c in rows).items(),key=lambda x:(-x[1],x[0])))

def age_buckets(rows,now):
    out=Counter()
    for c in rows:
        stamp=parse_dt(c.get('bet365_timestamp'))
        if not stamp:out['missing_timestamp']+=1;continue
        minutes=(now-stamp).total_seconds()/60
        if minutes<0:out['future']+=1
        elif minutes<=20:out['0_20m']+=1
        elif minutes<=60:out['20_60m']+=1
        elif minutes<=180:out['60_180m']+=1
        else:out['180m_plus']+=1
    return dict(out)

def bottleneck(funnel,decision):
    if decision.get('decision') in ('PAPER PICK','PLAY'):return 'Der er en kvalificeret modelbeslutning.'
    checks=[('candidate_rows','Ingen referencekandidater i den seneste kørsel.'),('fair_probability_rows','Referencekandidater mangler fair probability.'),('exact_bet365_rows','Ingen kandidater har eksakt Bet365-identitet.'),('fresh_exact_bet365_rows','Eksakte Bet365-priser er ikke friske nok til final gate.'),('reference_depth_ready_rows','Ingen friske eksakte kandidater har nok referencebøger.'),('positive_edge_rows','Ingen friske referenceklare kandidater har positiv edge mod Bet365.'),('ev_ready_rows','Ingen positive-edge kandidater passerer EV-kravet.'),('qualified_now_rows','Ingen kandidat passerer alle final-gate krav lige nu.')]
    for key,message in checks:
        if int(funnel.get(key) or 0)<=0:return message
    return decision.get('reason') or 'Final gate afviste den seneste kørsel.'

def main():
    now=datetime.now(timezone.utc); candidates=load_json(CANDIDATES,[]); decision=load_json(DECISION,{})
    bet365=load_json(BET365,{}); diagnostics=load_json(REFERENCE_DIAG,{}); market=load_json(MARKET_COVERAGE,{}); runs=read_jsonl(DECISION_RUNS)
    exact=[c for c in candidates if exact_identity(c)]; fresh=[c for c in exact if fresh_bet365(c,now)]
    min_books=int(engine.P.get('min_reference_books_for_play',3)); reference_ready=[c for c in fresh if int(c.get('books') or 0)>=min_books]
    positive_edge=[c for c in reference_ready if (candidate_edge(c)[0] is not None and candidate_edge(c)[0]>=float(engine.P.get('min_edge',0.02)))]
    ev_ready=[c for c in positive_edge if (candidate_edge(c)[1] is not None and candidate_edge(c)[1]>=float(engine.P.get('min_ev',0.025)))]
    qualified=[x for x in (engine.evaluate(c,now) for c in candidates) if x and x.get('qualified')]
    funnel={'candidate_rows':len(candidates),'fair_probability_rows':sum(1 for c in candidates if c.get('fair_probability') is not None),'reference_events':diagnostics.get('reference_events'),'exact_bet365_rows':len(exact),'fresh_exact_bet365_rows':len(fresh),'reference_depth_ready_rows':len(reference_ready),'positive_edge_rows':len(positive_edge),'ev_ready_rows':len(ev_ready),'qualified_now_rows':len(qualified),'decision_runs_recorded':len(runs)}
    diagnostics_out={'by_market':{'candidate':market_counts(candidates),'exact':market_counts(exact),'fresh':market_counts(fresh),'reference_ready':market_counts(reference_ready),'positive_edge':market_counts(positive_edge)},'exact_price_age_buckets':age_buckets(exact,now),'reference_depth_rejections_by_market':market_counts([c for c in fresh if int(c.get('books') or 0)<min_books])}
    provider={'generated_at':bet365.get('generated_at'),'available':provider_available(bet365),'bet365_events_available':bet365.get('bet365_events_available'),'events_queried':first_present(bet365,'events_queried','queried_events'),'provider_call_attempts':bet365.get('provider_call_attempts'),'provider_call_successes':bet365.get('provider_call_successes'),'odds_calls':bet365.get('odds_calls'),'odds_multi_calls':first_present(bet365,'odds_multi_calls','batch_attempts'),'fallback_odds_calls':first_present(bet365,'fallback_odds_calls','fallback_attempts'),'raw_market_observations':bet365.get('raw_market_observations'),'unique_markets':bet365.get('unique_markets') or market.get('unique_markets'),'matched_reference_candidates':bet365.get('matched_reference_candidates'),'errors':bet365.get('errors') or []}
    report={'generated_at':now.isoformat(),'mode':decision.get('mode') or engine.P.get('mode','PAPER'),'decision':decision.get('decision'),'reason':decision.get('reason'),'bottleneck':bottleneck(funnel,decision),'funnel':funnel,'funnel_diagnostics':diagnostics_out,'provider':provider,'policy':{'bankroll_dkk':engine.P.get('bankroll_dkk'),'min_edge':engine.P.get('min_edge'),'min_ev':engine.P.get('min_ev'),'max_price_age_minutes':engine.P.get('max_price_age_minutes'),'min_reference_books_for_play':engine.P.get('min_reference_books_for_play')}}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'decision':report['decision'],'bottleneck':report['bottleneck'],'funnel':funnel},ensure_ascii=False))

if __name__=='__main__':main()
