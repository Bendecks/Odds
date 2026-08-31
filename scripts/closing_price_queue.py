import json, pathlib, os
from datetime import datetime, timezone, timedelta
from settlement_schema import signal_key

SIGNALS=pathlib.Path('data/model_signals.jsonl')
CLOSES=pathlib.Path('data/model_closing_prices.jsonl')
OUT=pathlib.Path('output/closing_price_queue.json')
WINDOW_MINUTES=int(os.getenv('CLOSING_CAPTURE_WINDOW_MINUTES','30'))

def read(path):
    out=[]
    if not path.exists():return out
    for line in path.read_text().splitlines():
        try:out.append(json.loads(line))
        except Exception:pass
    return out

def main():
    now=datetime.now(timezone.utc); signals=[x for x in read(SIGNALS) if x.get('decision') in ('PAPER PICK','PLAY')]
    captured={str(x.get('signal_key')) for x in read(CLOSES) if x.get('signal_key') and x.get('closing_odds')}
    due=[]; upcoming=[]; missed=[]
    for x in signals:
        key=signal_key(x)
        if key in captured:continue
        try:start=datetime.fromisoformat(str(x.get('commence_time')).replace('Z','+00:00')).astimezone(timezone.utc)
        except Exception:continue
        row={'signal_key':key,'event':x.get('event'),'market':x.get('market'),'pick':x.get('pick'),'taken_odds':x.get('odds'),'commence_time':x.get('commence_time'),'model_version':x.get('model_version'),'bet365_event_id':x.get('bet365_event_id'),'event_match_method':x.get('event_match_method')}
        if start-timedelta(minutes=WINDOW_MINUTES)<=now<=start:due.append(row)
        elif now<start-timedelta(minutes=WINDOW_MINUTES):upcoming.append(row)
        else:missed.append(row)
    report={'generated_at':now.isoformat(),'capture_window_minutes':WINDOW_MINUTES,'due_now':len(due),'upcoming':len(upcoming),'missed_without_close':len(missed),'due':due[:100],'missed':missed[:100]}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('due','missed')},ensure_ascii=False))
if __name__=='__main__':main()
