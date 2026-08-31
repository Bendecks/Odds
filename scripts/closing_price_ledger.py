import json, pathlib
from settlement_schema import clv_pct

PATH=pathlib.Path('data/model_closing_prices.jsonl')
SIGNALS=pathlib.Path('data/model_signals.jsonl')
STATUS=pathlib.Path('output/closing_price_status.json')

def read(path):
    out=[]
    if not path.exists():return out
    for line in path.read_text().splitlines():
        try:out.append(json.loads(line))
        except Exception:pass
    return out

def signal_odds():
    out={}
    for x in read(SIGNALS):
        key=str(x.get('signal_key') or '').strip()
        if not key:continue
        try:odds=float(x.get('odds'))
        except Exception:continue
        if odds>1:out[key]=odds
    return out

def main():
    rows=read(PATH); canonical=signal_odds(); valid=[]; seen=set(); missing_signal_odds=0
    for x in reversed(rows):
        key=str(x.get('signal_key') or '').strip()
        try:close=float(x.get('closing_odds'))
        except Exception:continue
        if not key or close<=1 or key in seen:continue
        seen.add(key); row=dict(x); row['closing_odds']=close
        taken=canonical.get(key)
        if taken is None:missing_signal_odds+=1
        row['taken_odds']=taken
        row['clv_pct']=clv_pct({'odds':taken,'closing_odds':close}) if taken is not None else None
        valid.append(row)
    valid=list(reversed(valid))[-2000:]
    PATH.parent.mkdir(exist_ok=True);PATH.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in valid))
    report={'records':len(valid),'with_clv':sum(x.get('clv_pct') is not None for x in valid),'missing_canonical_signal_odds':missing_signal_odds};STATUS.parent.mkdir(exist_ok=True);STATUS.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
