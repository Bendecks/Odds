import json, pathlib
from datetime import datetime, timezone

SIGNALS=pathlib.Path('data/model_signals.jsonl')
SETTLED=pathlib.Path('data/model_settlements.jsonl')
OUT=pathlib.Path('output/model_settlement_queue.json')

def read(path):
    out=[]
    if not path.exists(): return out
    for line in path.read_text().splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def signal_key(x):
    return '|'.join(str(x.get(k,'')) for k in ('event','market','pick','price_timestamp','model_version'))

def main():
    signals=[x for x in read(SIGNALS) if x.get('decision') in ('PAPER PICK','PLAY')]
    settled=read(SETTLED); settled_keys={str(x.get('signal_key','')) for x in settled}
    now=datetime.now(timezone.utc); pending=[]; future=[]
    for x in signals:
        k=signal_key(x)
        if k in settled_keys: continue
        try: start=datetime.fromisoformat(str(x.get('commence_time')).replace('Z','+00:00')).astimezone(timezone.utc)
        except Exception: start=None
        row={'signal_key':k,'event':x.get('event'),'market':x.get('market'),'pick':x.get('pick'),'odds':x.get('odds'),'stake_dkk':x.get('stake'),'fair_probability':x.get('fair_probability'),'commence_time':x.get('commence_time'),'model_version':x.get('model_version'),'price_timestamp':x.get('price_timestamp')}
        (pending if start and start<now else future).append(row)
    report={'generated_at':now.isoformat(),'actionable_signals':len(signals),'settled':len(settled_keys),'awaiting_settlement':len(pending),'not_started_or_unknown':len(future),'pending':pending[:100]}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({k:v for k,v in report.items() if k!='pending'},ensure_ascii=False))
if __name__=='__main__': main()
