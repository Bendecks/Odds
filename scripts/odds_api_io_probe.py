import os, json, pathlib, requests
from datetime import datetime, timezone

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
KEY = os.getenv('ODDS_API_IO_KEY','')
BASE = 'https://api.odds-api.io/v3'
SPORTS = ['football','tennis','basketball','ice-hockey']

COMMON_PATHS = [
    '/sports',
    '/leagues',
    '/events',
    '/odds',
    '/markets',
    '/bookmakers',
]

SPORT_PATH_TEMPLATES = [
    '/sports/{sport}/leagues',
    '/sports/{sport}/events',
    '/sports/{sport}/odds',
    '/sports/{sport}/matches',
    '/sports/{sport}/fixtures',
    '/{sport}/leagues',
    '/{sport}/events',
    '/{sport}/odds',
    '/{sport}/matches',
    '/{sport}/fixtures',
    '/events/{sport}',
    '/odds/{sport}',
]

PARAM_VARIANTS = [
    {},
    {'sport':'football'},
    {'sport':'tennis'},
    {'sport':'basketball'},
    {'sport':'ice-hockey'},
    {'sports':'football,tennis,basketball,ice-hockey'},
    {'regions':'eu,uk'},
    {'markets':'h2h,spreads,totals'},
    {'sport':'football','regions':'eu,uk'},
    {'sport':'football','markets':'h2h,spreads,totals'},
    {'sport':'football','regions':'eu,uk','markets':'h2h,spreads,totals'},
]

EVENT_ID_KEYS = ['id','eventId','event_id','matchId','fixtureId']
EVENT_PATH_TEMPLATES = [
    '/events/{event_id}',
    '/event/{event_id}',
    '/odds/{event_id}',
    '/events/{event_id}/odds',
    '/event/{event_id}/odds',
    '/matches/{event_id}/odds',
    '/fixtures/{event_id}/odds',
]
EVENT_PARAM_VARIANTS = [
    lambda eid: {'eventId':eid},
    lambda eid: {'event_id':eid},
    lambda eid: {'id':eid},
    lambda eid: {'matchId':eid},
    lambda eid: {'fixtureId':eid},
    lambda eid: {'eventId':eid,'markets':'h2h,spreads,totals'},
]

def safe_preview(x, n=1200):
    try:
        s = json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x
    except Exception:
        s = str(x)
    return s[:n]

def get_json_or_text(url, params):
    params=dict(params or {})
    params['apiKey']=KEY
    r=requests.get(url,params=params,timeout=25)
    try:
        body=r.json()
    except Exception:
        body=r.text[:1500]
    return {
        'url': r.url.replace(KEY,'***'),
        'status': r.status_code,
        'ok': r.ok,
        'content_type': r.headers.get('content-type',''),
        'body': body,
        'preview': safe_preview(body),
    }

def is_useful(res):
    if not res.get('ok'): return False
    body=res.get('body')
    if isinstance(body,list): return len(body)>0
    if isinstance(body,dict): return len(body)>0 and not body.get('error')
    return False

def extract_event_ids(body, limit=5):
    found=[]
    def scan(obj):
        if len(found)>=limit: return
        if isinstance(obj,dict):
            for k in EVENT_ID_KEYS:
                if k in obj and obj[k] not in found:
                    found.append(obj[k])
                    if len(found)>=limit: return
            for v in obj.values(): scan(v)
        elif isinstance(obj,list):
            for item in obj: scan(item)
    scan(body)
    return [str(x) for x in found if x is not None]

def main():
    results=[]
    useful=[]
    event_ids=[]
    if not KEY:
        results.append({'error':'Missing ODDS_API_IO_KEY'})
    else:
        tests=[]
        for path in COMMON_PATHS:
            for params in PARAM_VARIANTS:
                tests.append((BASE+path,params,'common'))
        for sport in SPORTS:
            for tmpl in SPORT_PATH_TEMPLATES:
                for params in [{}, {'regions':'eu,uk'}, {'markets':'h2h,spreads,totals'}, {'regions':'eu,uk','markets':'h2h,spreads,totals'}]:
                    tests.append((BASE+tmpl.format(sport=sport),params,f'sport:{sport}'))
        for url,params,kind in tests:
            res=get_json_or_text(url,params)
            res.update({'kind':kind,'params':params})
            results.append({k:v for k,v in res.items() if k!='body'})
            if is_useful(res):
                useful.append(res)
                event_ids += extract_event_ids(res.get('body'),limit=10)
        # event-id dependent probes
        event_ids=list(dict.fromkeys(event_ids))[:10]
        for eid in event_ids:
            for tmpl in EVENT_PATH_TEMPLATES:
                res=get_json_or_text(BASE+tmpl.format(event_id=eid),{})
                res.update({'kind':'event_path','event_id':eid})
                results.append({k:v for k,v in res.items() if k!='body'})
                if is_useful(res): useful.append(res)
            for param_fn in EVENT_PARAM_VARIANTS:
                for path in ['/odds','/events','/event','/markets']:
                    res=get_json_or_text(BASE+path,param_fn(eid))
                    res.update({'kind':'event_param','event_id':eid})
                    results.append({k:v for k,v in res.items() if k!='body'})
                    if is_useful(res): useful.append(res)
    write_outputs(results,useful,event_ids)

def write_outputs(results,useful,event_ids):
    data={
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'total_tests':len(results),
        'useful_count':len(useful),
        'event_ids_found':event_ids,
        'useful':[{k:v for k,v in r.items() if k!='body'} for r in useful[:50]],
        'all_results':results,
    }
    (OUT/'odds_api_io_probe.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with open(OUT/'odds_api_io_probe.md','w',encoding='utf-8') as f:
        f.write('# odds-api.io probe v2\n\n')
        f.write(f"Generated: {data['generated_at']}\n\n")
        f.write(f"Tests: {len(results)} | Useful 2xx: {len(useful)} | Event IDs found: {len(event_ids)}\n\n")
        f.write('## Event IDs found\n')
        f.write('\n'.join([f'- {x}' for x in event_ids]) or 'None')
        f.write('\n\n## Useful responses\n')
        if not useful:
            f.write('No useful 2xx response found.\n\n')
        for i,r in enumerate(useful[:30],1):
            f.write(f"{i}. {r.get('status')} | {r.get('kind')} | {r.get('url')}\n")
            f.write(f"Params: `{json.dumps(r.get('params',{}),ensure_ascii=False)}`\n")
            f.write('```\n'+r.get('preview','')+'\n```\n\n')
        f.write('## Failure sample\n')
        failures=[r for r in results if not r.get('ok')]
        for r in failures[-60:]:
            f.write(f"- {r.get('status')} | {r.get('kind')} | {r.get('url')} | {r.get('preview')}\n")
    print(f"odds-api.io probe v2 complete. useful={len(useful)} tests={len(results)} event_ids={len(event_ids)}")

if __name__ == '__main__':
    main()
