import json, pathlib
from collections import Counter

SRC=pathlib.Path('data/value_candidates.json'); OUT=pathlib.Path('output/reference_coverage_report.json')

def main():
    try:rows=json.loads(SRC.read_text())
    except Exception:rows=[]
    q=Counter(str(r.get('reference_quality') or 'legacy') for r in rows); books=Counter(int(r.get('books',0) or 0) for r in rows); picks=Counter('draw' if str(r.get('pick','')).lower()=='draw' else 'team' for r in rows)
    report={'reference_observations':len(rows),'quality_counts':dict(q),'book_depth':{str(k):v for k,v in sorted(books.items())},'pick_types':dict(picks),'play_eligible_reference_depth':sum(1 for r in rows if int(r.get('books',0) or 0)>=3)}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
