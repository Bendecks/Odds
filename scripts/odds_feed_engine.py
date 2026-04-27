import os, json, pathlib, requests, statistics
from datetime import datetime, timezone

BASE = pathlib.Path('.')
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)
API_KEY = os.getenv('THE_ODDS_API_KEY','')

SPORT_ALLOW = [
  'tennis_atp', 'tennis_wta', 'basketball_nba', 'icehockey_nhl',
  'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
  'soccer_italy_serie_a', 'soccer_uefa_champs_league', 'soccer_denmark_superliga'
]

results = []
summary = 'ingen spil nu'

if API_KEY:
    try:
        url = 'https://api.the-odds-api.com/v4/sports/upcoming/odds'
        params = {
          'apiKey': API_KEY,
          'regions': 'eu',
          'markets': 'h2h',
          'oddsFormat': 'decimal'
        }
        r = requests.get(url, params=params, timeout=45)
        r.raise_for_status()
        data = r.json()
        for game in data:
            sk = game.get('sport_key','')
            if sk not in SPORT_ALLOW:
                continue
            books = game.get('bookmakers', [])
            if len(books) < 2:
                continue
            market_prices = {}
            for b in books:
                for m in b.get('markets', []):
                    if m.get('key') == 'h2h':
                        for o in m.get('outcomes', []):
                            market_prices.setdefault(o['name'], []).append(float(o['price']))
            for team, prices in market_prices.items():
                if len(prices) < 2:
                    continue
                best = max(prices)
                avg = statistics.mean(prices)
                edge = (best / avg) - 1
                if best < 1.25:
                    continue
                if edge < 0.03:
                    continue
                conf = min(9.5, round(6 + edge*40,1))
                results.append({
                    'event': f"{game.get('home_team')} vs {game.get('away_team')}",
                    'selection': team,
                    'odds': round(best,2),
                    'avg_market_odds': round(avg,2),
                    'edge_pct': round(edge*100,1),
                    'sport': sk,
                    'commence_time': game.get('commence_time'),
                    'confidence': conf
                })
        results = sorted(results, key=lambda x:(x['confidence'], x['edge_pct']), reverse=True)[:10]
        if results:
            summary = f"{len(results)} value spots fundet via odds feed"
    except Exception as e:
        summary = f'Feed error: {e}'
else:
    summary = 'Missing THE_ODDS_API_KEY'

with open(OUT/'odds_feed.json','w',encoding='utf-8') as f:
    json.dump({'summary':summary,'picks':results}, f, ensure_ascii=False, indent=2)

with open(OUT/'odds_feed.md','w',encoding='utf-8') as f:
    f.write('# ODDS FEED PICKS\n\n'+summary+'\n\n')
    for i,p in enumerate(results,1):
        f.write(f"## {i}. {p['event']}\n")
        f.write(f"- Pick: {p['selection']}\n- Odds: {p['odds']}\n- Market avg: {p['avg_market_odds']}\n- Edge: {p['edge_pct']}%\n- Confidence: {p['confidence']}/10\n- Sport: {p['sport']}\n\n")
print(summary)
