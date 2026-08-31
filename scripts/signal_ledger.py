import json, pathlib
from datetime import datetime, timezone
from settlement_schema import signal_key

DECISION=pathlib.Path('output/latest_decision.json'); LEDGER=pathlib.Path('data/model_signals.jsonl'); STATUS=pathlib.Path('output/signal_ledger_status.json'); MAX_ROWS=2000

def key(x):return '|'.join(str(x.get(k,'')) for k in ('event','market','pick','odds','model_version','price_timestamp'))
def decision_rows(decision, recorded_at):
    picks=decision.get('picks') if isinstance(decision.get('picks'),list) else []
    if picks:
        rows=[]
        for pick in picks:
            row={'recorded_at':recorded_at,**pick}
            row['signal_key']=signal_key(row)
            rows.append(row)
        return rows
    row={'recorded_at':recorded_at,**decision}
    if row.get('decision') in ('PAPER PICK','PLAY'):
        row['signal_key']=signal_key(row)
    return [row]

def main():
    try:d=json.loads(DECISION.read_text())
    except Exception:return
    recorded_at=datetime.now(timezone.utc).isoformat(); rows=decision_rows(d,recorded_at); old=[]
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:old.append(json.loads(line))
            except Exception:pass
    for row in rows:
        if not old or key(old[-1])!=key(row) or old[-1].get('decision')!=row.get('decision'):old.append(row)
    old=old[-MAX_ROWS:]; LEDGER.parent.mkdir(exist_ok=True); LEDGER.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in old))
    status={'signal_ledger_rows':len(old),'latest':d.get('decision'),'latest_pick_count':len(rows) if d.get('decision') in ('PAPER PICK','PLAY') else 0,'updated_at':recorded_at}; STATUS.parent.mkdir(exist_ok=True); STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(status,ensure_ascii=False))
if __name__=='__main__':main()
