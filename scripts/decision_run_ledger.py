import json, pathlib
from datetime import datetime, timezone

DECISION=pathlib.Path('output/latest_decision.json')
CANDIDATES=pathlib.Path('data/value_candidates.json')
BET365=pathlib.Path('output/bet365_join_status.json')
REFERENCE=pathlib.Path('output/the_odds_feed_status.json')
LEDGER=pathlib.Path('data/decision_runs.jsonl')
STATUS=pathlib.Path('output/decision_run_status.json')
MAX_ROWS=2000

def load(path, default):
    try:return json.loads(path.read_text())
    except Exception:return default

def main():
    decision=load(DECISION,{})
    candidates=load(CANDIDATES,[])
    bet365=load(BET365,{})
    reference=load(REFERENCE,{})
    verified=[x for x in candidates if x.get('bet365_verified')]
    fair=[x for x in candidates if x.get('fair_probability') is not None]
    row={
      'evaluated_at':datetime.now(timezone.utc).isoformat(),
      'decision':decision.get('decision'),
      'candidate_rows':len(candidates),
      'fair_probability_rows':len(fair),
      'bet365_verified_rows':len(verified),
      'reference_events':reference.get('events_seen'),
      'reference_observations':reference.get('reference_observations'),
      'bet365_events_queried':bet365.get('queried_events'),
      'bet365_exact_matches':bet365.get('exact_reference_matches'),
      'bet365_provider_available':bet365.get('provider_available'),
      'reason':decision.get('reason')
    }
    old=[]
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:old.append(json.loads(line))
            except Exception:pass
    old.append(row);old=old[-MAX_ROWS:]
    LEDGER.parent.mkdir(exist_ok=True);LEDGER.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in old))
    status={'evaluation_runs':len(old),'latest':row}
    STATUS.parent.mkdir(exist_ok=True);STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(status,ensure_ascii=False))
if __name__=='__main__':main()
