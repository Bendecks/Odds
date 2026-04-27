import os, json, pathlib, requests
from collections import Counter, defaultdict

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
API_KEY = os.getenv('THE_ODDS_API_KEY','')

payload = {
    'ok': False,
    'summary': {},
    'sports': {},
    'games_sample': [],
    'bookmaker_counts': {},
    'market_counts': {},
    'errors': []
}

if not API_KEY:
    payload['errors'].append('Missing THE_ODDS_API_KEY')
else:
    try:
        url = 'https://api.the-odds-api.com/v4/sports/upcoming/odds'
        params = {
            'apiKey': API_KEY,
            'regions': 'eu,uk',
            'markets': 'h2h,spreads,totals',
            'oddsFormat': 'decimal'
        }
        r = requests.get(url, params=params, timeout=60)
        payload['status_code'] = r.status_code
        payload['headers'] = {k:v for k,v in r.headers.items() if k.lower().startswith('x-')}
        r.raise_for_status()
        data = r.json()
        payload['ok'] = True
        payload['summary']['total_games'] = len(data)

        sports = Counter()
        bookmaker_counts = Counter()
        market_counts = Counter()
        sport_examples = defaultdict(list)

        for game in data:
            sk = game.get('sport_key','unknown')
            st = game.get('sport_title','unknown')
            sports[(sk,st)] += 1
            books = game.get('bookmakers', [])
            bookmaker_counts[len(books)] += 1
            for b in books:
                for m in b.get('markets', []):
                    market_counts[m.get('key','unknown')] += 1
            if len(sport_examples[sk]) < 3:
                sport_examples[sk].append({
                    'sport_key': sk,
                    'sport_title': st,
                    'commence_time': game.get('commence_time'),
                    'home_team': game.get('home_team'),
                    'away_team': game.get('away_team'),
                    'bookmakers': [b.get('key') for b in books[:8]],
                    'markets': sorted(list({m.get('key') for b in books for m in b.get('markets', [])})),
                    'first_prices': [
                        {
                            'bookmaker': b.get('key'),
                            'markets': [
                                {'market': m.get('key'), 'outcomes': m.get('outcomes', [])[:4]}
                                for m in b.get('markets', [])[:3]
                            ]
                        } for b in books[:2]
                    ]
                })

        payload['sports'] = [
            {'sport_key': k[0], 'sport_title': k[1], 'games': v, 'examples': sport_examples[k[0]]}
            for k,v in sports.most_common()
        ]
        payload['bookmaker_counts'] = dict(sorted(bookmaker_counts.items()))
        payload['market_counts'] = dict(market_counts.most_common())
        payload['games_sample'] = data[:5]
    except Exception as e:
        payload['errors'].append(str(e))

with open(OUT/'raw_feed_scan.json','w',encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

with open(OUT/'raw_feed_scan.md','w',encoding='utf-8') as f:
    f.write('# RAW FEED SCAN\n\n')
    f.write(f"OK: {payload.get('ok')}\n\n")
    if payload.get('errors'):
        f.write('## Errors\n')
        for e in payload['errors']:
            f.write(f'- {e}\n')
        f.write('\n')
    f.write('## Summary\n')
    for k,v in payload.get('summary',{}).items():
        f.write(f'- {k}: {v}\n')
    f.write('\n## Rate / quota headers\n')
    for k,v in payload.get('headers',{}).items():
        f.write(f'- {k}: {v}\n')
    f.write('\n## Market counts\n')
    for k,v in payload.get('market_counts',{}).items():
        f.write(f'- {k}: {v}\n')
    f.write('\n## Bookmaker count distribution\n')
    for k,v in payload.get('bookmaker_counts',{}).items():
        f.write(f'- {k} bookmakers: {v} games\n')
    f.write('\n## Sports returned\n')
    for s in payload.get('sports',[])[:50]:
        f.write(f"### {s['sport_title']} — `{s['sport_key']}` — {s['games']} games\n")
        for ex in s.get('examples',[])[:2]:
            f.write(f"- {ex.get('home_team')} vs {ex.get('away_team')} at {ex.get('commence_time')} | books={len(ex.get('bookmakers',[]))} | markets={','.join(ex.get('markets',[]))}\n")
        f.write('\n')

print(json.dumps(payload.get('summary',{}), ensure_ascii=False))
