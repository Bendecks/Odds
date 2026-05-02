import json, pathlib
from collections import defaultdict

OUT = pathlib.Path('output')
PAPER = OUT / 'paper_bets.json'
FEEDBACK = OUT / 'v9_feedback.json'
SUMMARY = OUT / 'v9_feedback.md'


def load():
    if PAPER.exists():
        return json.loads(PAPER.read_text())
    return {}


def analyze(bets):
    stats = defaultdict(lambda: {'bets':0,'wins':0,'profit':0})
    for b in bets:
        if b.get('status')!='settled': continue
        key = f"{b.get('market')}|odds_{int(float(b.get('odds') or 0))}"
        stats[key]['bets']+=1
        if b.get('result')=='win': stats[key]['wins']+=1
        stats[key]['profit']+=float(b.get('profit') or 0)
    out={}
    for k,v in stats.items():
        if v['bets']<5: continue
        hit=v['wins']/v['bets']*100
        roi=v['profit']/(v['bets'] or 1)
        out[k]={'bets':v['bets'],'hit_rate':round(hit,1),'roi_per_bet':round(roi,2)}
    return out


def main():
    data=load()
    bets=data.get('bets',[])
    feedback=analyze(bets)
    FEEDBACK.write_text(json.dumps(feedback,indent=2))

    with open(SUMMARY,'w') as f:
        f.write('V9 PERFORMANCE FEEDBACK\n\n')
        for k,v in feedback.items():
            f.write(f"{k}: bets={v['bets']} hit={v['hit_rate']}% roi={v['roi_per_bet']}\n")

    print('V9 feedback generated')

if __name__=='__main__': main()
