import json, pathlib, collections

OBS=pathlib.Path('data/unibet_observations.jsonl')
OUT=pathlib.Path('data/value_candidates.json')

DIRECT={'ML':'h2h','Moneyline':'h2h','H2H':'h2h','1X2':'h2h','Totals':'totals','Goals Over/Under':'totals','Spread':'spreads'}

def novig(prices):
    inv={k:1/v for k,v in prices.items() if v and v>1}
    total=sum(inv.values())
    return {k:v/total for k,v in inv.items()} if len(inv)>=2 and total>0 else {}

def main():
    rows=[]
    if OBS.exists():
        for line in OBS.read_text().splitlines():
            try: rows.append(json.loads(line))
            except Exception: pass
    grouped=collections.defaultdict(list)
    for r in rows:
        market=DIRECT.get(str(r.get('market')))
        if market: grouped[(r.get('event_id'),r.get('event'),r.get('commence_time'),market,r.get('line'))].append(r)
    out=[]
    for (eid,event,start,market,line),items in grouped.items():
        prices={str(x.get('selection')):float(x['odds']) for x in items if x.get('odds') is not None}
        fair=novig(prices)
        for selection,p in fair.items():
            pick=selection
            if market=='h2h':
                home=str(items[0].get('home') or '');away=str(items[0].get('away') or '')
                pick=home if selection=='home' else away if selection=='away' else 'Draw' if selection=='draw' else selection
            elif market=='totals': pick=selection.title()
            elif market=='spreads':
                home=str(items[0].get('home') or '');away=str(items[0].get('away') or '')
                pick=home if selection=='home' else away if selection=='away' else selection
            row={'event':event,'event_id':eid,'commence_time':start,'market':market,'pick':pick,'reference_odds':round(1/p,3),'fair_probability':round(p,6),'books':1,'reference_books':['Unibet'],'reference_quality':'weak','discovery_eligible':True,'bookmaker':'UNIBET_REFERENCE','bet365_verified':False,'model_version':'odds-api-io-unibet-v1'}
            if line is not None: row['line']=line
            out.append(row)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(out)} Unibet reference candidates from {len(grouped)} market groups')

if __name__=='__main__': main()
