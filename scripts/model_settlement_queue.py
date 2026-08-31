import json, pathlib, os
from datetime import datetime, timezone, timedelta
from settlement_schema import signal_key, settlement_key, valid_settlement

SIGNALS=pathlib.Path('data/model_signals.jsonl')
SETTLED=pathlib.Path('data/model_settlements.jsonl')
OUT=pathlib.Path('output/model_settlement_queue.json')
GRACE_HOURS=int(os.getenv('SETTLEMENT_GRACE_HOURS','3'))

def read(path):
    out=[]
    if not path.exists(): return out
    for line in path.read_text().splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def main():
    signals=[x for x in read(SIGNALS) if x.get('decision') in ('PAPER PICK','PLAY')]
    settlements=read(SETTLED); settled_keys={settlement_key(x) for x in settlements if valid_settlement(x)}
    now=datetime.now(timezone.utc); pending=[]; future=[]
    for x in signals:
        k=signal_key(x)
        if k in settled_keys: continue
        try: start=datetime.fromisoformat(str(x.get('commence_time')).replace('Z','+00:00')).astimezone(timezone.utc)
        except Exception: start=None
        row={'signal_key':k,'event':x.get('event'),'event_id':x.get('event_id'),'sport':x.get('sport'),'market':x.get('market'),'pick':x.get('pick'),'odds':x.get('odds'),'stake_dkk':x.get('stake'),'fair_probability':x.get('fair_probability'),'commence_time':x.get('commence_time'),'model_version':x.get('model_version'),'price_timestamp':x.get('price_timestamp'),'bet365_event_id':x.get('bet365_event_id'),'event_match_method':x.get('event_match_method')}
        mature=bool(start and start+timedelta(hours=GRACE_HOURS)<=now)
        (pending if mature else future).append(row)
    report={'generated_at':now.isoformat(),'actionable_signals':len(signals),'valid_settlements':len(settled_keys),'settlement_grace_hours':GRACE_HOURS,'awaiting_settlement':len(pending),'not_mature_or_unknown':len(future),'pending':pending[:100]}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({k:v for k,v in report.items() if k!='pending'},ensure_ascii=False))
if __name__=='__main__': main()
