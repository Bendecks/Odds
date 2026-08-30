import json, pathlib
from collections import Counter, defaultdict

OBS=pathlib.Path('data/bet365_observations.jsonl'); OUT=pathlib.Path('output/market_signal_inventory.json')

def main():
    rows=[]
    if OBS.exists():
        for line in OBS.read_text().splitlines():
            try:rows.append(json.loads(line))
            except Exception:pass
    by_market=Counter(); events=defaultdict(set); priced=defaultdict(list)
    for r in rows:
        m=str(r.get('market') or 'unknown'); eid=str(r.get('event_id') or '')
        try:o=float(r.get('odds'))
        except Exception:continue
        by_market[m]+=1; events[m].add(eid); priced[m].append(o)
    inventory=[]
    for m,n in by_market.most_common():
        vals=priced[m]
        inventory.append({'market':m,'observations':n,'events':len(events[m]),'min_odds':min(vals) if vals else None,'max_odds':max(vals) if vals else None,'reference_model_status':'h2h-supported' if m=='ML' else 'unmodelled'})
    report={'observations':len(rows),'market_families':len(inventory),'inventory':inventory}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'observations':len(rows),'market_families':len(inventory)},ensure_ascii=False))
if __name__=='__main__':main()
