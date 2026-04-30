import os, json, pathlib, requests
from datetime import datetime, timezone

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
KEY = os.getenv('ODDS_API_IO_KEY','')

BASES = [
    'https://api.odds-api.io',
    'https://api.oddsapi.io',
    'https://api.odds-api.io/v1',
    'https://api.odds-api.io/v2',
    'https://api.odds-api.io/v3',
]

PATHS = [
    '/sports',
    '/leagues',
    '/events',
    '/odds',
    '/markets',
    '/v1/sports',
    '/v1/leagues',
    '/v1/events',
    '/v1/odds',
    '/v2/sports',
    '/v2/leagues',
    '/v2/events',
    '/v2/odds',
    '/v3/sports',
    '/v3/leagues',
    '/v3/events',
    '/v3/odds',
]

AUTH_VARIANTS = [
    ('apiKey_param', lambda: ({'apiKey': KEY}, {})),
    ('api_key_param', lambda: ({'api_key': KEY}, {})),
    ('key_param', lambda: ({'key': KEY}, {})),
    ('x_api_key_header', lambda: ({}, {'x-api-key': KEY})),
    ('bearer_header', lambda: ({}, {'Authorization': f'Bearer {KEY}'})),
]

EXTRA_PARAMS = [
    {},
    {'sport':'soccer'},
    {'sport':'football'},
    {'sport':'tennis'},
    {'sport':'basketball'},
    {'sports':'soccer,tennis,basketball,icehockey'},
    {'regions':'eu,uk'},
    {'markets':'h2h,spreads,totals'},
    {'sport':'soccer','regions':'eu,uk','markets':'h2h,spreads,totals'},
]

def safe_preview(x, n=900):
    try:
        s = json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x
    except Exception:
        s = str(x)
    return s[:n]

def request_try(url, params, headers):
    try:
        r = requests.get(url, params=params, headers=headers, timeout=25)
        content_type = r.headers.get('content-type','')
        try:
            body = r.json()
        except Exception:
            body = r.text[:1000]
        return {
            'url': r.url.replace(KEY, '***') if KEY else r.url,
            'status': r.status_code,
            'content_type': content_type,
            'ok': r.ok,
            'preview': safe_preview(body),
        }
    except Exception as e:
        return {'url': url, 'status': 'EXCEPTION', 'ok': False, 'preview': str(e)[:500]}

def main():
    results=[]
    if not KEY:
        results.append({'error':'Missing ODDS_API_IO_KEY'})
    else:
        for base in BASES:
            for path in PATHS:
                url = base.rstrip('/') + path
                for auth_name, auth_fn in AUTH_VARIANTS:
                    auth_params, headers = auth_fn()
                    for extra in EXTRA_PARAMS:
                        params = dict(auth_params)
                        params.update(extra)
                        res = request_try(url, params, headers)
                        res.update({'auth':auth_name,'extra':extra,'base':base,'path':path})
                        results.append(res)
                        # Stop early for obviously useful JSON responses
                        if res.get('ok') and res.get('status') == 200 and ('json' in res.get('content_type','').lower() or res.get('preview','').startswith(('{','['))):
                            raise SystemExit(write_outputs(results, early=True))
    write_outputs(results, early=False)

def write_outputs(results, early=False):
    useful=[r for r in results if r.get('ok')]
    data={'generated_at':datetime.now(timezone.utc).isoformat(),'early_stop':early,'total_tests':len(results),'useful_count':len(useful),'useful':useful[:20],'all_results':results}
    (OUT/'odds_api_io_probe.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with open(OUT/'odds_api_io_probe.md','w',encoding='utf-8') as f:
        f.write('# odds-api.io probe\n\n')
        f.write(f"Generated: {data['generated_at']}\n\n")
        f.write(f"Tests: {len(results)} | Useful 2xx: {len(useful)} | Early stop: {early}\n\n")
        f.write('## Useful responses\n')
        if not useful:
            f.write('No 2xx response found. See errors below.\n\n')
        for i,r in enumerate(useful[:20],1):
            f.write(f"{i}. {r.get('status')} | {r.get('auth')} | {r.get('url')}\n```\n{r.get('preview')}\n```\n\n")
        f.write('## Recent failures/sample\n')
        for r in results[-40:]:
            if r.get('ok'): continue
            f.write(f"- {r.get('status')} | {r.get('auth')} | {r.get('url')} | {r.get('preview')}\n")
    print(f"odds-api.io probe complete. useful={len(useful)} tests={len(results)}")
    return 0

if __name__ == '__main__':
    main()
