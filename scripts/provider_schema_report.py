import collections,json,pathlib

OBS=pathlib.Path('data/bet365_observations.jsonl')
OUT=pathlib.Path('output/bet365_selection_schema.json')
TARGET_OUT=pathlib.Path('output/bet365_target_schema.json')
TARGET_MARKET_TERMS=(
 'exact total','exact goals','correct score','team total','team goals','asian handicap','spread'
)

def load_rows():
 rows=[]
 if not OBS.exists():return rows
 for line in OBS.read_text().splitlines():
  try:rows.append(json.loads(line))
  except Exception:pass
 return rows

def market_schema(items):
 names=collections.Counter(str(r.get('raw_selection_name')) for r in items if r.get('raw_selection_name') not in (None,''))
 labels=collections.Counter(str(r.get('raw_selection_label')) for r in items if r.get('raw_selection_label') not in (None,''))
 fields=collections.Counter(str(r.get('selection') or 'unknown') for r in items)
 lines=collections.Counter(str(r.get('line')) for r in items if r.get('line') not in (None,''))
 examples=[];seen=set()
 for r in items:
  key=(r.get('raw_selection_name'),r.get('raw_selection_label'),r.get('selection'),r.get('line'))
  if key in seen:continue
  seen.add(key);examples.append({'raw_selection_name':r.get('raw_selection_name'),'raw_selection_label':r.get('raw_selection_label'),'selection':r.get('selection'),'line':r.get('line')})
  if len(examples)>=12:break
 return {'observations':len(items),'selection_fields':fields.most_common(20),'raw_selection_names':names.most_common(30),'raw_selection_labels':labels.most_common(30),'lines':lines.most_common(30),'schema_examples':examples}

def is_target_market(market):
 key=str(market).lower()
 return any(term in key for term in TARGET_MARKET_TERMS)

def main():
 rows=load_rows();markets={}
 grouped=collections.defaultdict(list)
 for r in rows:grouped[str(r.get('market') or 'unknown')].append(r)
 for market,items in grouped.items():markets[market]=market_schema(items)
 ordered=dict(sorted(markets.items(),key=lambda kv:(-kv[1]['observations'],kv[0])))
 report={'observations':len(rows),'markets':ordered}
 targets={market:data for market,data in ordered.items() if is_target_market(market)}
 target_report={'observations':sum(v['observations'] for v in targets.values()),'markets':targets}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 TARGET_OUT.write_text(json.dumps(target_report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'observations':len(rows),'markets':len(markets),'target_markets':len(targets)}))
if __name__=='__main__':main()
