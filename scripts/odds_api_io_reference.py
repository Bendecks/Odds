import json, pathlib, collections

UNIBET=pathlib.Path('data/unibet_observations.jsonl')
BET365=pathlib.Path('data/bet365_observations.jsonl')
OUT=pathlib.Path('data/value_candidates.json')
SHADOW_OUT=pathlib.Path('output/devig_shadow_comparison.json')

DIRECT={'ml':'h2h','moneyline':'h2h','h2h':'h2h','1x2':'h2h','totals':'totals','goals over/under':'totals','spread':'spreads','alternative asian handicap':'spreads'}
REFERENCE_TRANSPORT='odds-api.io'
REFERENCE_ECONOMIC_SOURCE='unibet'
REFERENCE_EVIDENCE_FAMILY='market_price'
REFERENCE_VERSION='odds-api-io-unibet-v2'

def load(path):
    rows=[]
    if path.exists():
        for line in path.read_text().splitlines():
            try: rows.append(json.loads(line))
            except Exception: pass
    return rows

def novig(prices):
    inv={k:1/v for k,v in prices.items() if v and v>1}
    total=sum(inv.values())
    return {k:v/total for k,v in inv.items()} if len(inv)>=2 and total>0 else {}

def power_novig(prices):
    inv={k:1/v for k,v in prices.items() if v and v>1}
    if len(inv)<2:return {}
    total=sum(inv.values())
    if total<=0:return {}
    if abs(total-1.0)<1e-12:return dict(inv)
    low,high=0.01,10.0
    def summed(exp):return sum(v**exp for v in inv.values())
    for _ in range(100):
        mid=(low+high)/2
        if summed(mid)>1:low=mid
        else:high=mid
    exp=(low+high)/2
    probs={k:v**exp for k,v in inv.items()}
    norm=sum(probs.values())
    return {k:v/norm for k,v in probs.items()} if norm>0 else {}

def key(row,market=None):
    return (str(row.get('event_id')),market or DIRECT.get(str(row.get('market','')).lower()),row.get('line'),str(row.get('selection')))

def reference_provenance():
    return {'transport_provider_id':REFERENCE_TRANSPORT,'economic_source_id':REFERENCE_ECONOMIC_SOURCE,'evidence_family':REFERENCE_EVIDENCE_FAMILY,'model_or_feed_version':REFERENCE_VERSION}

def unique_economic_source_count(sources):
    return len({str(x.get('economic_source_id') or '').strip().lower() for x in sources if str(x.get('economic_source_id') or '').strip()})

def devig_shadow(prices):
    production=novig(prices)
    power=power_novig(prices)
    out={}
    for selection,p in production.items():
        row={'production_method':'multiplicative','production_probability':round(p,6)}
        if selection in power:
            row['power_probability']=round(power[selection],6)
            row['power_delta']=round(power[selection]-p,6)
        out[selection]=row
    return out

def shadow_report(records, market_groups):
    usable=[r for r in records if r.get('power_probability') is not None]
    abs_deltas=[abs(float(r.get('power_delta') or 0)) for r in usable]
    max_record=max(usable,key=lambda r:abs(float(r.get('power_delta') or 0)),default=None)
    return {
        'method':'multiplicative_vs_power',
        'production_method':'multiplicative',
        'shadow_method':'power',
        'production_impact':'none',
        'market_groups':market_groups,
        'selections_compared':len(usable),
        'avg_abs_probability_delta':round(sum(abs_deltas)/len(abs_deltas),6) if abs_deltas else 0,
        'max_abs_probability_delta':round(max(abs_deltas),6) if abs_deltas else 0,
        'max_delta_record':max_record,
    }

def main():
    unibet=load(UNIBET); bet365=load(BET365)
    grouped=collections.defaultdict(list)
    for r in unibet:
        market=DIRECT.get(str(r.get('market','')).lower())
        if market: grouped[(r.get('event_id'),r.get('event'),r.get('commence_time'),market,r.get('line'))].append(r)
    bet365_prices={key(r):r for r in bet365 if DIRECT.get(str(r.get('market','')).lower())}
    out=[]; shadow_records=[]
    for (eid,event,start,market,line),items in grouped.items():
        prices={str(x.get('selection')):float(x['odds']) for x in items if x.get('odds') is not None}
        fair=novig(prices)
        shadow=devig_shadow(prices)
        provenance=[reference_provenance()]
        books=unique_economic_source_count(provenance)
        for selection,p in fair.items():
            home=str(items[0].get('home') or ''); away=str(items[0].get('away') or '')
            pick=selection
            if market=='h2h': pick=home if selection=='home' else away if selection=='away' else 'Draw' if selection=='draw' else selection
            elif market=='totals': pick=selection.title()
            elif market=='spreads': pick=home if selection=='home' else away if selection=='away' else selection
            row={'event':event,'event_id':eid,'commence_time':start,'market':market,'pick':pick,'reference_odds':round(1/p,3),'fair_probability':round(p,6),'devig_method':'multiplicative','devig_shadow':shadow.get(selection,{}),'books':books,'reference_books':['Unibet'],'reference_sources':provenance,'reference_quality':'weak','discovery_eligible':True,'bookmaker':'UNIBET_REFERENCE','bet365_verified':False,'model_version':REFERENCE_VERSION,'bet365_event_id':eid,'event_match_method':'exact'}
            if shadow.get(selection):
                shadow_records.append({'event_id':eid,'event':event,'market':market,'line':line,'selection':selection,'pick':pick,**shadow[selection]})
            if line is not None: row['line']=line
            b=bet365_prices.get((str(eid),market,line,selection))
            if b and float(b.get('odds') or 0)>1:
                row.update({'bet365_odds':float(b['odds']),'bet365_timestamp':b.get('observed_at') or b.get('timestamp'),'bet365_provider_updated_at':b.get('timestamp'),'bet365_verified':True,'bet365_source':'odds-api.io','bet365_market':b.get('market'),'execution_source':{'transport_provider_id':'odds-api.io','economic_source_id':'bet365','evidence_family':'execution_price','model_or_feed_version':'odds-api-io-bet365-v1'}})
            out.append(row)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    SHADOW_OUT.parent.mkdir(exist_ok=True)
    SHADOW_OUT.write_text(json.dumps(shadow_report(shadow_records,len(grouped)),ensure_ascii=False,indent=2)+'\n')
    print(f'{len(out)} Unibet reference candidates from {len(grouped)} market groups; {sum(1 for x in out if x.get("bet365_verified"))} exact Bet365 prices')

if __name__=='__main__': main()
