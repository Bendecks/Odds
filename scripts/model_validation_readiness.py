import json
import pathlib
from collections import Counter

SIGNALS=pathlib.Path('data/model_signals.jsonl')
SETTLED=pathlib.Path('data/model_settlements.jsonl')
OUT=pathlib.Path('output/model_validation_readiness.json')


def rows(path):
    out=[]
    if not path.exists(): return out
    for line in path.read_text().splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out


def f(v):
    try: return float(v)
    except Exception: return None


def build(signals, settled):
    actionable=[x for x in signals if x.get('decision') in ('PAPER PICK','PLAY')]
    decisive=[x for x in settled if x.get('result') in ('win','loss')]
    stake=sum(f(x.get('stake_dkk') or x.get('paper_stake')) or 0 for x in decisive)
    profit=sum(f(x.get('profit_dkk') or x.get('profit')) or 0 for x in decisive)
    clvs=[f(x.get('clv_pct')) for x in decisive if f(x.get('clv_pct')) is not None]
    briers=[]
    for x in decisive:
        p=f(x.get('fair_probability'))
        if p is None or not 0 <= p <= 1: continue
        y=1.0 if x.get('result')=='win' else 0.0
        briers.append((p-y)**2)
    models=Counter(str(x.get('model_version') or 'unknown') for x in actionable)
    return {
        'new_model_only': True,
        'signals': len(signals),
        'actionable_signals': len(actionable),
        'settled_decisive_bets': len(decisive),
        'stake_dkk': round(stake,2),
        'profit_dkk': round(profit,2),
        'roi_pct': round(100*profit/stake,2) if stake else None,
        'clv_observations': len(clvs),
        'mean_clv_pct': round(sum(clvs)/len(clvs),3) if clvs else None,
        'calibration_observations': len(briers),
        'brier_score': round(sum(briers)/len(briers),6) if briers else None,
        'model_versions': dict(models),
        'promotion_ready': False,
        'promotion_blockers': [
            'requires at least 300 settled new-model bets',
            'requires positive out-of-sample ROI with uncertainty analysis',
            'requires positive CLV evidence',
            'requires calibration review',
            'LIVE promotion must not be automatic from a single threshold crossing'
        ],
        'note': 'Legacy paper bets are intentionally excluded from new-model validation.'
    }


def main():
    report=build(rows(SIGNALS),rows(SETTLED))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__': main()
