import json, pathlib
from datetime import datetime, timezone

DECISION=pathlib.Path('output/latest_decision.json'); LEDGER=pathlib.Path('data/model_signals.jsonl'); STATUS=pathlib.Path('output/signal_ledger_status.json'); MAX_ROWS=2000

def key(x):return '|'.join(str(x.get(k,'')) for k in ('event','market','pick','odds','model_version','price_timestamp'))

def main():
    try:d=json.loads(DECISION.read_text())
    except Exception:return
    row={'recorded_at':datetime.now(timezone.utc).isoformat(),**d}; old=[]
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:old.append(json.loads(line))
            except Exception:pass
    if not old or key(old[-1])!=key(row) or old[-1].get('decision')!=row.get('decision'):old.append(row)
    old=old[-MAX_ROWS:]; LEDGER.parent.mkdir(exist_ok=True); LEDGER.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in old))
    status={'signal_ledger_rows':len(old),'latest':d.get('decision'),'updated_at':row['recorded_at']}; STATUS.parent.mkdir(exist_ok=True); STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(status,ensure_ascii=False))
if __name__=='__main__':main()
