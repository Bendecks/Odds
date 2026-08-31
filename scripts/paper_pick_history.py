import json, pathlib

SIGNALS=pathlib.Path('data/model_signals.jsonl')
SETTLEMENTS=pathlib.Path('data/model_settlements.jsonl')
CLOSES=pathlib.Path('data/model_closing_prices.jsonl')
OUT=pathlib.Path('output/paper_pick_history.json')
MAX_PUBLIC_ROWS=100

def read_jsonl(path):
    rows=[]
    if not path.exists(): return rows
    for line in path.read_text().splitlines():
        try: rows.append(json.loads(line))
        except Exception: pass
    return rows

def main():
    signals=[x for x in read_jsonl(SIGNALS) if x.get('decision') in ('PAPER PICK','PLAY') and x.get('signal_key')]
    settled={str(x.get('signal_key')):x for x in read_jsonl(SETTLEMENTS) if x.get('signal_key')}
    closes={str(x.get('signal_key')):x for x in read_jsonl(CLOSES) if x.get('signal_key')}
    rows=[]
    for s in signals:
        key=str(s['signal_key']); result=settled.get(key,{}); close=closes.get(key,{})
        try: stake=float(s.get('stake') if s.get('stake') is not None else s.get('stake_dkk'))
        except Exception: stake=None
        try: odds=float(s.get('odds'))
        except Exception: odds=None
        outcome=result.get('result'); profit=None
        if stake is not None and odds is not None:
            if outcome=='win': profit=round(stake*(odds-1),2)
            elif outcome=='loss': profit=round(-stake,2)
            elif outcome in ('push','void'): profit=0.0
        rows.append({'signal_key':key,'recorded_at':s.get('recorded_at'),'commence_time':s.get('commence_time'),'event':s.get('event'),'market':s.get('market'),'pick':s.get('pick'),'odds':odds,'stake_dkk':stake,'edge':s.get('edge'),'ev':s.get('ev'),'reference_books':s.get('reference_books'),'result':outcome or 'open','profit_dkk':profit,'closing_odds':close.get('closing_odds') or result.get('closing_odds'),'clv_pct':close.get('clv_pct'),'model_version':s.get('model_version')})
    rows=rows[-MAX_PUBLIC_ROWS:]
    decisive=[x for x in rows if x['result'] in ('win','loss')]
    total_stake=sum((x['stake_dkk'] or 0) for x in decisive); total_profit=sum((x['profit_dkk'] or 0) for x in decisive)
    report={'paper_picks':len(rows),'open_picks':sum(x['result']=='open' for x in rows),'settled_picks':sum(x['result'] in ('win','loss','push','void') for x in rows),'decisive_picks':len(decisive),'total_stake_dkk':round(total_stake,2),'profit_dkk':round(total_profit,2),'roi_pct':round(total_profit/total_stake*100,2) if total_stake else None,'rows':list(reversed(rows))}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))
if __name__=='__main__':main()
