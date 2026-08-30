import json, pathlib
from datetime import datetime, timezone

OBS=pathlib.Path('data/bet365_observations.jsonl')
HISTORY=pathlib.Path('data/observation_snapshots.jsonl')
MAX_SNAPSHOTS=120

def main():
    if not OBS.exists():return
    rows=[]
    for line in OBS.read_text().splitlines():
        try:rows.append(json.loads(line))
        except Exception:pass
    event_ids={str(r.get('event_id')) for r in rows if r.get('event_id')}
    markets={str(r.get('market')) for r in rows if r.get('market')}
    snap={'timestamp':datetime.now(timezone.utc).isoformat(),'observations':len(rows),'events':len(event_ids),'markets':len(markets)}
    old=[]
    if HISTORY.exists():
        for line in HISTORY.read_text().splitlines():
            try:old.append(json.loads(line))
            except Exception:pass
    old.append(snap); old=old[-MAX_SNAPSHOTS:]
    HISTORY.parent.mkdir(exist_ok=True); HISTORY.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in old))
    print(json.dumps(snap,ensure_ascii=False))
if __name__=='__main__':main()
