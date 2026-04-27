import os, json, pathlib, requests, statistics
from datetime import datetime, timezone

BASE = pathlib.Path('.')
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)
API_KEY = os.getenv('THE_ODDS_API_KEY','')

# FLOODGATES MODE: debug only. Shows broad candidates so we can inspect the feed.
# Not automatic betting advice.
MODE = 'FLOODGATES_DEBUG'

SPORT_PREFIX_ALLOW = [
  'tennis_atp', 'tennis_wta', 'basketball_nba', 'icehockey_nhl',
  'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
  'soccer_italy_serie_a', 'soccer_uefa_champs_league', 'soccer_denmark_superliga',
  'soccer_france_ligue_one', 'soccer_france_ligue_two', 'soccer_portugal_primeira_liga'
]

MIN_BOOKS = 2
MIN_ODDS = 1.20
MAX_ODDS = 8.00
MAX_HOURS_AHEAD = 168

results = []
summary = 'ingen kandidater'

def sport_allowed(sport_key):
    return any(sport_key.startswith(prefix) for prefix in SPORT_PREFIX_ALLOW)

def parse_time(s):
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None

def no_vig_probs(outcome_prices):
    implied = {k: 1/v for k,v in outcome_prices.items() if v and v > 1}
    total = sum(implied.values())
    if total <= 0:
        return {}
    return {k: implied[k]/total for k in implied}

if API_KEY:
    try:
        url = 'https://api.the-odds-api.com/v4/sports/upcoming/odds'
        params = {
          'apiKey': API_KEY,
          'regions': 'eu,uk',
          'markets': 'h2h,spreads,totals',
          'oddsFormat': 'decimal'
        }
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        now = datetime.now(timezone.utc)

        for game in data:
            sk = game.get('sport_key','')
            event = f"{game.get('home_team')} vs {game.get('away_team')}"
            commence = parse_time(game.get('commence_time',''))
            if not sport_allowed(sk) or not commence:
                continue
            hours_ahead = (commence - now).total_seconds() / 3600
            if hours_ahead <= 0 or hours_ahead > MAX_HOURS_AHEAD:
                continue

            books = game.get('bookmakers', [])
            if len(books) < MIN_BOOKS:
                continue

            market_prices = {}
            for b in books:
                for m in b.get('markets', []):
                    if m.get('key') != 'h2h':
                        continue
                    for o in m.get('outcomes', []):
                        try:
                            price = float(o['price'])
                        except Exception:
                            continue
                        if 1.01 <= price <= 30:
                            market_prices.setdefault(o['name'], []).append(price)

            medians = {name: statistics.median(prices) for name, prices in market_prices.items() if len(prices) >= MIN_BOOKS}
            fair_probs = no_vig_probs(medians)

            for team, prices in market_prices.items():
                if len(prices) < MIN_BOOKS:
                    continue
                prices = sorted(prices)
                best = max(prices)
                median = statistics.median(prices)
                avg = statistics.mean(prices)
                if best < MIN_ODDS or best > MAX_ODDS:
                    continue
                fair_prob = fair_probs.get(team)
                implied_at_best = 1 / best
                value_gap = (fair_prob - implied_at_best) if fair_prob else 0
                edge_vs_median = (best / median) - 1 if median else 0
                spread_ratio = best / median if median else 999
                debug_score = round(edge_vs_median * 100 + value_gap * 100 - max(0, spread_ratio - 1.5) * 20, 2)
                results.append({
                    'event': event,
                    'selection': team,
                    'odds': round(best,2),
                    'median_market_odds': round(median,2),
                    'avg_market_odds': round(avg,2),
                    'edge_pct': round(edge_vs_median*100,1),
                    'value_gap_pct': round(value_gap*100,1),
                    'spread_ratio': round(spread_ratio,2),
                    'bookmakers_count': len(prices),
                    'sport': sk,
                    'commence_time': game.get('commence_time'),
                    'test_stake_kr': 0,
                    'mode': MODE,
                    'debug_score': debug_score
                })
        results = sorted(results, key=lambda x:(x['debug_score'], x['bookmakers_count']), reverse=True)[:30]
        summary = f"FLOODGATES_DEBUG: {len(results)} rå kandidater vist — ikke automatisk spil" if results else 'ingen rå kandidater fundet'
    except Exception as e:
        summary = f'Feed error: {e}'
else:
    summary = 'Missing THE_ODDS_API_KEY'

payload = {'mode': MODE, 'summary': summary, 'picks': results}
with open(OUT/'odds_feed.json','w',encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

with open(OUT/'odds_feed.md','w',encoding='utf-8') as f:
    f.write('# ODDS FEED PICKS — FLOODGATES DEBUG\n\n'+summary+'\n\n')
    for i,p in enumerate(results,1):
        f.write(f"## {i}. {p['event']}\n")
        f.write(f"- Pick: {p['selection']}\n- Odds: {p['odds']}\n- Median market: {p['median_market_odds']}\n- Edge vs median: {p['edge_pct']}%\n- No-vig value gap: {p['value_gap_pct']}%\n- Spread ratio: {p['spread_ratio']}\n- Books: {p['bookmakers_count']}\n- Debug score: {p['debug_score']}\n- Sport: {p['sport']}\n- Start: {p['commence_time']}\n- Mode: {p['mode']}\n\n")
print(summary)
