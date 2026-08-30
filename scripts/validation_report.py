import json,pathlib
from collections import defaultdict

SRC=pathlib.Path('output/paper_bets.json'); OUT=pathlib.Path('output/validation_report.json')
def f(v):
    try:return float(v or 0)
    except:return 0.0

def main():
    data=json.loads(SRC.read_text()) if SRC.exists() else {'bets':[]}; settled=[b for b in data.get('bets',[]) if b.get('status')=='settled' and b.get('result') in ('win','loss')]
    stake=sum(f(b.get('paper_stake')) for b in settled); profit=sum(f(b.get('profit')) for b in settled); wins=sum(b.get('result')=='win' for b in settled)
    buckets=defaultdict(lambda:{'bets':0,'stake':0.0,'profit':0.0})
    for b in settled:
        key=f"{b.get('sport','unknown')}|{b.get('market','unknown')}"; x=buckets[key]; x['bets']+=1; x['stake']+=f(b.get('paper_stake')); x['profit']+=f(b.get('profit'))
    segments={k:{'bets':v['bets'],'roi_pct':round(100*v['profit']/v['stake'],2) if v['stake'] else 0} for k,v in buckets.items()}
    report={'settled_decisive_bets':len(settled),'wins':wins,'losses':len(settled)-wins,'stake':round(stake,2),'profit':round(profit,2),'roi_pct':round(100*profit/stake,2) if stake else 0,'segments':segments,'clv_available':any(b.get('closing_odds') for b in settled),'calibration_available':any(b.get('fair_probability') for b in settled),'promotion_ready':False,'note':'Legacy paper history is diagnostic only; it does not validate the new market-consensus model.'}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
