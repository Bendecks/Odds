import json, pathlib
from settlement_schema import clv_pct

PATH=pathlib.Path('data/model_closing_prices.jsonl')
STATUS=pathlib.Path('output/closing_price_status.json')

def read():
    out=[]
    if not PATH.exists():return out
    for line in PATH.read_text().splitlines():
        try:out.append(json.loads(line))
        except Exception:pass
    return out

def main():
    rows=read(); valid=[]; seen=set()
    for x in reversed(rows):
        key=str(x.get('signal_key') or '').strip()
        try:close=float(x.get('closing_odds'))
        except Exception:continue
        if not key or close<=1 or key in seen:continue
        seen.add(key); row=dict(x); row['closing_odds']=close; row['clv_pct']=clv_pct({'odds':x.get('taken_odds'),'closing_odds':close});valid.append(row)
    valid=list(reversed(valid))[-2000:]
    PATH.parent.mkdir(exist_ok=True);PATH.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in valid))
    report={'records':len(valid),'with_clv':sum(x.get('clv_pct') is not None for x in valid)};STATUS.parent.mkdir(exist_ok=True);STATUS.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
