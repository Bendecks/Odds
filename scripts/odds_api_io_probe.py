import os, json, pathlib, requests
from datetime import datetime, timezone

OUT=pathlib.Path('output'); OUT.mkdir(exist_ok=True)
KEY=os.getenv('ODDS_API_IO_KEY','')
BASE='https://api.odds-api.io/v3'
SPORTS=['football','tennis','basketball','ice-hockey']
EVENT_KEYS=['id','eventId','event_id','matchId','fixtureId']
PREFERRED={
 'football':['england-premier-league','spain-laliga','italy-serie-a','germany-bundesliga','france-ligue-1','denmark-superliga'],
 'tennis':['atp-atp-madrid-spain-men-singles','wta-wta-madrid-spain-women-singles','atp-atp-rome-italy-men-singles'],
 'basketball':['usa-nba','euroleague','spain-acb'],
 'ice-hockey':['usa-nhl','finland-liiga','germany-del']
}
SEED_IDS=['66053430','68643372','70379124','68687616','67149472','67698134','68042456','71204436','71188222','67171884']

def preview(x,n=1200):
    try: s=json.dumps(x,ensure_ascii=False) if not isinstance(x,str) else x
    except Exception: s=str(x)
    return s[:n]

def call(url,params=None):
    p=dict(params or {}); p['apiKey']=KEY
    try:
        r=requests.get(url,params=p,timeout=25)
        try: body=r.json()
        except Exception: body=r.text[:1500]
        return {'url':r.url.replace(KEY,'***'),'status':r.status_code,'ok':r.ok,'body':body,'preview':preview(body)}
    except Exception as e:
        return {'url':url,'status':'EXCEPTION','ok':False,'body':str(e),'preview':str(e)[:500]}

def useful(r):
    b=r.get('body')
    return r.get('ok') and ((isinstance(b,list) and len(b)>0) or (isinstance(b,dict) and len(b)>0 and not b.get('error')))

def strip(r): return {k:v for k,v in r.items() if k!='body'}

def ids(obj,limit=50):
    out=[]
    def scan(x):
        if len(out)>=limit: return
        if isinstance(x,dict):
            for k in EVENT_KEYS:
                if k in x and x[k] not in out: out.append(x[k])
            for v in x.values(): scan(v)
        elif isinstance(x,list):
            for y in x: scan(y)
    scan(obj)
    return [str(x) for x in out if x is not None]

def leagues(body):
    if not isinstance(body,list): return []
    rows=[{'name':x.get('name'),'slug':x.get('slug'),'eventsCount':x.get('eventsCount',0)} for x in body if isinstance(x,dict) and x.get('slug')]
    return sorted(rows,key=lambda x:int(x.get('eventsCount') or 0),reverse=True)

def main():
    results=[]; good=[]; found_ids=[]; bysport={}
    if not KEY:
        results.append({'error':'Missing ODDS_API_IO_KEY'}); write(results,good,found_ids,bysport); return
    for sport in SPORTS:
        r=call(BASE+'/leagues',{'sport':sport}); r.update({'kind':'league_list','sport':sport,'params':{'sport':sport}})
        results.append(strip(r))
        if useful(r): good.append(r); bysport[sport]=leagues(r['body'])[:20]
    for sport in SPORTS:
        slugs=list(dict.fromkeys(PREFERRED.get(sport,[])+[x['slug'] for x in bysport.get(sport,[])[:8]]))
        for slug in slugs:
            variants=[
              (BASE+'/events',{'sport':sport,'league':slug}), (BASE+'/events',{'sport':sport,'leagueSlug':slug}),
              (BASE+'/matches',{'sport':sport,'league':slug}), (BASE+'/fixtures',{'sport':sport,'league':slug}),
              (BASE+'/odds',{'sport':sport,'league':slug}), (BASE+f'/leagues/{slug}/events',{'sport':sport}),
              (BASE+f'/leagues/{slug}/odds',{'sport':sport}), (BASE+f'/{sport}/{slug}/events',{}),
              (BASE+f'/{sport}/{slug}/odds',{}), (BASE+f'/sports/{sport}/leagues/{slug}/events',{}),
              (BASE+f'/sports/{sport}/leagues/{slug}/odds',{})]
            for url,p in variants:
                r=call(url,p); r.update({'kind':'league_probe','sport':sport,'league':slug,'params':p})
                results.append(strip(r))
                if useful(r): good.append(r); found_ids+=ids(r['body'],20)
    found_ids=list(dict.fromkeys(found_ids+SEED_IDS))[:25]
    for eid in found_ids:
        variants=[(BASE+'/odds',{'eventId':eid}), (BASE+'/odds',{'id':eid}), (BASE+'/odds',{'eventId':eid,'markets':'h2h,spreads,totals'}),
                  (BASE+'/markets',{'eventId':eid}), (BASE+'/events',{'eventId':eid}), (BASE+f'/events/{eid}',{}),
                  (BASE+f'/events/{eid}/odds',{}), (BASE+f'/odds/{eid}',{}), (BASE+f'/matches/{eid}/odds',{})]
        for url,p in variants:
            r=call(url,p); r.update({'kind':'event_odds_probe','event_id':eid,'params':p})
            results.append(strip(r))
            if useful(r): good.append(r)
    write(results,good,found_ids,bysport)

def write(results,good,found_ids,bysport):
    data={'generated_at':datetime.now(timezone.utc).isoformat(),'total_tests':len(results),'useful_count':len(good),'event_ids_found':found_ids,'leagues_by_sport':bysport,'useful':[strip(r) for r in good[:80]],'all_results':results}
    (OUT/'odds_api_io_probe.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with open(OUT/'odds_api_io_probe.md','w',encoding='utf-8') as f:
        f.write('# odds-api.io probe v3\n\n')
        f.write(f"Generated: {data['generated_at']}\n\nTests: {len(results)} | Useful 2xx: {len(good)} | Event IDs: {len(found_ids)}\n\n")
        f.write('## League samples\n')
        for sport,ls in bysport.items():
            f.write(f'### {sport}\n')
            for l in ls[:10]: f.write(f"- {l.get('slug')} ({l.get('eventsCount')}) — {l.get('name')}\n")
        f.write('\n## Event IDs found\n'+('\n'.join([f'- {x}' for x in found_ids]) or 'None')+'\n\n')
        f.write('## Useful responses\n')
        for i,r in enumerate(good[:50],1):
            f.write(f"{i}. {r.get('status')} | {r.get('kind')} | {r.get('url')}\nParams: `{json.dumps(r.get('params',{}),ensure_ascii=False)}`\n```\n{r.get('preview','')}\n```\n\n")
        f.write('## Failure sample\n')
        for r in [x for x in results if not x.get('ok')][-80:]: f.write(f"- {r.get('status')} | {r.get('kind')} | {r.get('url')} | {r.get('preview')}\n")
    print(f"odds-api.io probe v3 complete. useful={len(good)} tests={len(results)} ids={len(found_ids)}")

if __name__=='__main__': main()
