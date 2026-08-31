import json, pathlib, random
from collections import Counter
from settlement_schema import settlement_key, valid_settlement, profit_dkk, clv_pct, normalize_result

SIGNALS=pathlib.Path('data/model_signals.jsonl'); SETTLED=pathlib.Path('data/model_settlements.jsonl'); OUT=pathlib.Path('output/model_validation_readiness.json')

def rows(path):
    out=[]
    if not path.exists(): return out
    for line in path.read_text().splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def f(v):
    try:return float(v)
    except Exception:return None

def roi_ci(decisive, samples=2000, seed=260831):
    units=[]
    for x in decisive:
        stake=f(x.get('stake_dkk') if x.get('stake_dkk') is not None else x.get('stake')); profit=profit_dkk(x)
        if stake is None or stake<=0 or profit is None:continue
        units.append((stake,profit))
    if len(units)<2:return None
    rng=random.Random(seed); vals=[]; n=len(units)
    for _ in range(samples):
        draw=[units[rng.randrange(n)] for _ in range(n)]; stake=sum(x[0] for x in draw); profit=sum(x[1] for x in draw)
        if stake>0:vals.append(100*profit/stake)
    if not vals:return None
    vals.sort(); lo=vals[int(.025*(len(vals)-1))]; hi=vals[int(.975*(len(vals)-1))]
    return [round(lo,2),round(hi,2)]

def calibration(decisive):
    buckets={}
    for x in decisive:
        p=f(x.get('fair_probability'))
        if p is None or not 0<=p<=1:continue
        y=1.0 if normalize_result(x.get('result'))=='win' else 0.0
        lo=min(9,int(p*10))/10; key=f'{lo:.1f}-{lo+.1:.1f}';b=buckets.setdefault(key,{'n':0,'pred_sum':0.0,'wins':0.0});b['n']+=1;b['pred_sum']+=p;b['wins']+=y
    out=[]; total=sum(x['n'] for x in buckets.values());ece=0.0
    for key in sorted(buckets):
        b=buckets[key];pred=b['pred_sum']/b['n'];actual=b['wins']/b['n'];gap=abs(pred-actual);ece+=gap*b['n']
        out.append({'bucket':key,'n':b['n'],'mean_predicted':round(pred,4),'actual_win_rate':round(actual,4),'absolute_gap':round(gap,4)})
    return out,round(ece/total,6) if total else None

def metrics(settled):
    valid=[x for x in settled if valid_settlement(x)]; decisive=[x for x in valid if normalize_result(x.get('result')) in ('win','loss')]
    stake=sum(f(x.get('stake_dkk') if x.get('stake_dkk') is not None else x.get('stake')) or 0 for x in decisive)
    profits=[profit_dkk(x) for x in decisive]; profit=sum(x for x in profits if x is not None)
    clvs=[clv_pct(x) for x in decisive]; clvs=[x for x in clvs if x is not None]
    briers=[]
    for x in decisive:
        p=f(x.get('fair_probability'))
        if p is None or not 0<=p<=1:continue
        y=1.0 if normalize_result(x.get('result'))=='win' else 0.0;briers.append((p-y)**2)
    ci=roi_ci(decisive);bins,ece=calibration(decisive)
    return {'valid_settlements':len(valid),'settled_decisive_bets':len(decisive),'stake_dkk':round(stake,2),'profit_dkk':round(profit,2),'roi_pct':round(100*profit/stake,2) if stake else None,'roi_bootstrap_95_pct':ci,'roi_lower_bound_pct':ci[0] if ci else None,'clv_observations':len(clvs),'mean_clv_pct':round(sum(clvs)/len(clvs),3) if clvs else None,'calibration_observations':len(briers),'brier_score':round(sum(briers)/len(briers),6) if briers else None,'expected_calibration_error':ece,'calibration_bins':bins}

def build(signals, settled):
    actionable=[x for x in signals if x.get('decision') in ('PAPER PICK','PLAY')]
    base=metrics(settled); models=Counter(str(x.get('model_version') or 'unknown') for x in actionable)
    versions={}
    for version in sorted({str(x.get('model_version') or 'unknown') for x in settled}):versions[version]=metrics([x for x in settled if str(x.get('model_version') or 'unknown')==version])
    current=str(actionable[-1].get('model_version') or 'unknown') if actionable else None
    return {'new_model_only':True,'signals':len(signals),'actionable_signals':len(actionable),'settlement_records':len(settled),**base,'model_versions':dict(models),'current_model_version':current,'settlement_metrics_by_model_version':versions,'promotion_ready':False,'promotion_blockers':['requires at least 300 settled new-model bets','requires positive out-of-sample ROI with uncertainty analysis','requires positive CLV evidence','requires calibration review','LIVE promotion must not be automatic from a single threshold crossing'],'note':'Legacy paper bets are intentionally excluded from new-model validation. Bootstrap ROI interval and calibration diagnostics are descriptive; they are not guarantees of future returns.'}

def main():
    report=build(rows(SIGNALS),rows(SETTLED)); OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
