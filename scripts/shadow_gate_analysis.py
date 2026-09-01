import json,pathlib
from datetime import datetime,timezone
import operational_status as ops

CAND=pathlib.Path('data/value_candidates.json')
OUT=pathlib.Path('output/shadow_gate_analysis.json')
SCENARIOS=(
 ('production',0.02,0.025,3,20),
 ('very_mild',0.015,0.02,3,20),
 ('mild',0.01,0.015,3,30),
 ('paper_data',0.005,0.01,3,60),
 ('positive_two_books',0.0,0.0,2,60),
)

def eligible(c,now,min_edge,min_ev,min_books,max_age):
 if not ops.exact_identity(c):return False
 stamp=ops.parse_dt(c.get('bet365_timestamp'))
 if not stamp:return False
 age=(now-stamp).total_seconds()/60
 if age<0 or age>max_age:return False
 if int(c.get('books') or 0)<min_books:return False
 edge,ev=ops.candidate_edge(c)
 if edge is None or ev is None:return False
 return edge>=min_edge and ev>=min_ev

def main():
 now=datetime.now(timezone.utc)
 try:candidates=json.loads(CAND.read_text())
 except Exception:candidates=[]
 scenarios=[]
 for name,min_edge,min_ev,min_books,max_age in SCENARIOS:
  rows=[c for c in candidates if eligible(c,now,min_edge,min_ev,min_books,max_age)]
  scenarios.append({'name':name,'min_edge':min_edge,'min_ev':min_ev,'min_reference_books':min_books,'max_price_age_minutes':max_age,'shadow_signals':len(rows),'unique_events':len({c.get('event_id') for c in rows if c.get('event_id')}),'by_market':dict(sorted({m:sum(1 for c in rows if c.get('market')==m) for m in {c.get('market') for c in rows}}.items()))})
 report={'generated_at':now.isoformat(),'candidate_rows':len(candidates),'note':'Diagnostic only. Does not alter PAPER PICK or LIVE gates.','scenarios':scenarios}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
