import json, math, pathlib, statistics

LEDGER=pathlib.Path('data/model_signals.jsonl')
OUT=pathlib.Path('output/model_validation_report.json')

def rows():
    out=[]
    if not LEDGER.exists(): return out
    for line in LEDGER.read_text().splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def num(v):
    try: return float(v)
    except Exception: return None

def main():
    data=rows(); picks=[x for x in data if x.get('decision') in ('PAPER PICK','PLAY')]
    settled=[x for x in picks if str(x.get('result','')).upper() in ('WIN','LOSS','PUSH','VOID')]
    decisive=[x for x in settled if str(x.get('result','')).upper() in ('WIN','LOSS')]
    stake=sum(num(x.get('stake')) or 0 for x in decisive); profit=0.0
    for x in decisive:
        s=num(x.get('stake')) or 0; o=num(x.get('odds')) or 0
        profit += s*(o-1) if str(x.get('result')).upper()=='WIN' else -s
    roi=(profit/stake*100) if stake else None
    clv=[]; brier=[]
    for x in decisive:
        close=num(x.get('closing_odds')); taken=num(x.get('odds')); p=num(x.get('fair_probability'))
        if close and close>1 and taken and taken>1: clv.append(taken/close-1)
        if p is not None and 0<=p<=1:
            y=1.0 if str(x.get('result')).upper()=='WIN' else 0.0; brier.append((p-y)**2)
    report={'signal_rows':len(data),'paper_or_live_picks':len(picks),'settled_picks':len(settled),'decisive_picks':len(decisive),'stake_dkk':round(stake,2),'profit_dkk':round(profit,2),'roi_pct':round(roi,2) if roi is not None else None,'mean_clv_pct':round(statistics.mean(clv)*100,3) if clv else None,'clv_samples':len(clv),'brier_score':round(statistics.mean(brier),6) if brier else None,'brier_samples':len(brier),'ready_for_live_evaluation':len(decisive)>=300 and roi is not None and roi>1 and bool(clv) and statistics.mean(clv)>0,'note':'New-model ledger only. Missing settlement or closing odds remain missing; no legacy results are mixed in.'}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__': main()
