import json, pathlib
from collections import Counter, defaultdict

OBS=pathlib.Path('data/bet365_observations.jsonl')
OUT=pathlib.Path('output/market_coverage_report.json')
CORE={'ML','Totals','Spread','Double Chance','Draw No Bet','Both Teams To Score','Corners Totals','Bookings Totals'}

def load():
    if not OBS.exists():return []
    rows=[]
    for line in OBS.read_text().splitlines():
        try:rows.append(json.loads(line))
        except Exception:pass
    return rows

def main():
    rows=load(); markets=Counter(); events=defaultdict(set); selections=Counter()
    for r in rows:
        m=str(r.get('market') or 'unknown'); eid=str(r.get('event_id') or r.get('event') or '')
        markets[m]+=1; events[m].add(eid); selections[(m,str(r.get('selection') or ''))]+=1
    coverage=[]
    for m,n in markets.most_common():
        coverage.append({'market':m,'observations':n,'events':len(events[m]),'core_family':m in CORE,'avg_observations_per_event':round(n/max(len(events[m]),1),2)})
    report={'observations':len(rows),'unique_markets':len(markets),'markets':coverage,'core_market_coverage':[x for x in coverage if x['core_family']]}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'observations':len(rows),'unique_markets':len(markets),'core_markets':report['core_market_coverage']},ensure_ascii=False))
if __name__=='__main__':main()
