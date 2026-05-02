import os, json, pathlib, requests
from datetime import datetime, timezone

OUT=pathlib.Path('output'); OUT.mkdir(exist_ok=True)
KEY=os.getenv('ODDS_API_IO_KEY','')
BASE='https://api.odds-api.io/v3'
SEED_IDS=['66053430','68643372','70379124']

def preview(x,n=1400):
    try: s=json.dumps(x,ensure_ascii=False) if not isinstance(x,str) else x
    except Exception: s=str(x)
    return s[:n]

def call(url,params=None,kind='test'):
    p=dict(params or {}); p['apiKey']=KEY
    try:
        r=requests.get(url,params=p,timeout=25)
        try: body=r.json()
        except Exception: body=r.text[:1500]
        return {'kind':kind,'url':r.url.replace(KEY,'***'),'status':r.status_code,'ok':r.ok,'body':body,'preview':preview(body),'params':params or {}}
    except Exception as e:
        return {'kind':kind,'url':url,'status':'EXCEPTION','ok':False,'body':str(e),'preview':str(e)[:500],'params':params or {}}

def useful(r):
    b=r.get('body')
    return r.get('ok') and ((isinstance(b,list) and len(b)>0) or (isinstance(b,dict) and len(b)>0 and not b.get('error')))

def strip(r): return {k:v for k,v in r.items() if k!='body'}

def event_ids(obj,limit=3):
    keys=['id','eventId','event_id','matchId','fixtureId']
    out=[]
    def scan(x):
        if len(out)>=limit: return
        if isinstance(x,dict):
            for k in keys:
                if k in x and x[k] not in out: out.append(x[k])
            for v in x.values(): scan(v)
        elif isinstance(x,list):
            for y in x: scan(y)
    scan(obj)
    return [str(x) for x in out]

def pick_league(body):
    if not isinstance(body,list): return None
    rows=[x for x in body if isinstance(x,dict) and x.get('slug')]
    rows=sorted(rows,key=lambda x:int(x.get('eventsCount') or 0),reverse=True)
    return rows[0] if rows else None

def main():
    results=[]; good=[]; ids=[]
    if not KEY:
        results.append({'error':'Missing ODDS_API_IO_KEY'}); write(results,good,ids,None); return
    # Max ~10 calls. Designed for 100/hour limit.
    r=call(BASE+'/leagues',{'sport':'football'},'league_list')
    results.append(strip(r))
    if useful(r): good.append(r)
    league=pick_league(r.get('body')) if useful(r) else None
    slug=league.get('slug') if league else 'england-premier-league'
    event_tests=[
        (BASE+'/events',{'sport':'football','league':slug}),
        (BASE+'/events',{'sport':'football','leagueSlug':slug}),
        (BASE+'/odds',{'sport':'football','league':slug}),
        (BASE+f'/leagues/{slug}/events',{'sport':'football'}),
        (BASE+f'/leagues/{slug}/odds',{'sport':'football'}),
    ]
    for url,p in event_tests:
        r=call(url,p,'league_to_events_or_odds')
        results.append(strip(r))
        if useful(r):
            good.append(r); ids += event_ids(r.get('body'),3)
            if ids: break
    ids=list(dict.fromkeys(ids+SEED_IDS))[:3]
    odds_tests=[]
    for eid in ids[:1]:
        odds_tests=[
            (BASE+'/odds',{'eventId':eid}),
            (BASE+'/events',{'eventId':eid}),
            (BASE+f'/events/{eid}',{}),
            (BASE+'/odds',{'id':eid}),
        ]
    for url,p in odds_tests:
        r=call(url,p,'event_to_odds')
        results.append(strip(r))
        if useful(r):
            good.append(r)
            break
    write(results,good,ids,league)

def write(results,good,ids,league):
    data={'generated_at':datetime.now(timezone.utc).isoformat(),'probe_version':'v4_low_request','total_tests':len(results),'useful_count':len(good),'league':league,'event_ids':ids,'useful':[strip(r) for r in good],'all_results':results}
    (OUT/'odds_api_io_probe.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with open(OUT/'odds_api_io_probe.md','w',encoding='utf-8') as f:
        f.write('# odds-api.io probe v4 — low request\n\n')
        f.write(f"Generated: {data['generated_at']}\n\nTests: {len(results)} | Useful 2xx: {len(good)}\n\n")
        f.write('## Selected league\n')
        f.write(json.dumps(league,ensure_ascii=False,indent=2) if league else 'None')
        f.write('\n\n## Event IDs\n'+('\n'.join([f'- {x}' for x in ids]) or 'None')+'\n\n')
        f.write('## Useful responses\n')
        for i,r in enumerate(good,1):
            f.write(f"{i}. {r.get('status')} | {r.get('kind')} | {r.get('url')}\nParams: `{json.dumps(r.get('params',{}),ensure_ascii=False)}`\n```\n{r.get('preview','')}\n```\n\n")
        f.write('## All results\n')
        for r in results:
            f.write(f"- {r.get('status')} | {r.get('kind')} | {r.get('url')} | {r.get('preview')}\n")
    print(f"probe v4 done tests={len(results)} useful={len(good)} ids={len(ids)}")

if __name__=='__main__': main()
