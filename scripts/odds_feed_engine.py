import os, json, pathlib, requests, statistics, math
from datetime import datetime, timezone

BASE = pathlib.Path('.')
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)
API_KEY = os.getenv('THE_ODDS_API_KEY','')

# TEST MODE: looser filters so we can inspect whether the feed produces realistic candidates.
# Do not treat these as automatic bets until we tighten the model again.
MODE = 'TEST_LOOSE'

SPORT_PREFIX_ALLOW = [
  'tennis_atp', 'tennis_wta', 'basketball_nba', 'icehockey_nhl',
  'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
  'soccer_italy_serie_a', 'soccer_uefa_champs_league', 'soccer_denmark_superliga'
]

MIN_BOOKS = 3
MIN_ODDS = 1.25
MAX_ODDS = 6.00
MIN_EDGE = 0.015
MAX_SPREAD_RATIO = 1.75
MAX_HOURS_AHEAD = 120
MIN_VALUE_GAP = 0.003

results = []
rejections = []
summary = 'ingen spil nu'

def sport_allowed(sport_key):
    return any(sport_key.startswith(prefix) for prefix in SPORT_PREFIX_ALLOW)

def reject(event, selection, reason):
    rejections.append({'event': event, 'selection': selection, 'reason': reason})

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
          'regions': 'eu',
          'markets': 'h2h',
          'oddsFormat': 'decimal'
        }
        r = requests.get(url, params=params, timeout=45)
        r.raise_for_status()
        data = r.json()
        now = datetime.now(timezone.utc)

        for game in data:
            sk = game.get('sport_key','')
            event = f"{game.get('home_team')} vs {game.get('away_team')}"
            commence = parse_time(game.get('commence_time',''))
            if not sport_allowed(sk):
                continue
            if not commence:
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
                    if m.get('key') == 'h2h':
                        for o in m.get('outcomes', []):
                            try:
                                price = float(o['price'])
                            except Exception:
                                continue
                            if 1.01 <= price <= 20:
                                market_prices.setdefault(o['name'], []).append(price)

            medians = {name: statistics.median(prices) for name, prices in market_prices.items() if len(prices) >= MIN_BOOKS}
            fair_probs = no_vig_probs(medians)

            for team, prices in market_prices.items():
                if len(prices) < MIN_BOOKS:
                    reject(event, team, 'too few bookmakers')
                    continue
                prices = sorted(prices)
                best = max(prices)
                median = statistics.median(prices)
                avg = statistics.mean(prices)
                if best < MIN_ODDS or best > MAX_ODDS:
                    reject(event, team, 'odds outside test range')
                    continue
                if median < MIN_ODDS or median > MAX_ODDS:
                    reject(event, team, 'median odds outside test range')
                    continue
                if best / median > MAX_SPREAD_RATIO:
                    reject(event, team, 'outlier best price')
                    continue
                edge_vs_median = (best / median) - 1
                if edge_vs_median < MIN_EDGE:
                    reject(event, team, 'edge too small')
                    continue
                fair_prob = fair_probs.get(team)
                if not fair_prob:
                    reject(event, team, 'missing fair probability')
                    continue
                implied_at_best = 1 / best
                value_gap = fair_prob - implied_at_best
                if value_gap < MIN_VALUE_GAP:
                    reject(event, team, 'no-vig value gap too small')
                    continue
                conf = round(min(8.0, 5.0 + edge_vs_median*18 + value_gap*15), 1)
                results.append({
                    'event': event,
                    'selection': team,
                    'odds': round(best,2),
                    'median_market_odds': round(median,2),
                    'avg_market_odds': round(avg,2),
                    'edge_pct': round(edge_vs_median*100,1),
                    'value_gap_pct': round(value_gap*100,1),
                    'sport': sk,
                    'commence_time': game.get('commence_time'),
                    'confidence': conf,
                    'stake_kr': 1,
                    'mode': MODE
                })
        results = sorted(results, key=lambda x:(x['confidence'], x['value_gap_pct'], x['edge_pct']), reverse=True)[:15]
        if results:
            summary = f"TEST_LOOSE: {len(results)} kandidater fundet via odds feed — ikke automatisk spil"
        else:
            summary = 'ingen test-kandidater fundet'
    except Exception as e:
        summary = f'Feed error: {e}'
else:
    summary = 'Missing THE_ODDS_API_KEY'

payload = {'mode': MODE, 'summary': summary, 'picks': results, 'rejections_sample': rejections[:50]}
with open(OUT/'odds_feed.json','w',encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

with open(OUT/'odds_feed.md','w',encoding='utf-8') as f:
    f.write('# ODDS FEED PICKS — TEST LOOSE\n\n'+summary+'\n\n')
    if not results:
        f.write('Ingen kandidater.\n\n')
    for i,p in enumerate(results,1):
        f.write(f"## {i}. {p['event']}\n")
        f.write(f"- Pick: {p['selection']}\n- Odds: {p['odds']}\n- Median market: {p['median_market_odds']}\n- Edge vs median: {p['edge_pct']}%\n- No-vig value gap: {p['value_gap_pct']}%\n- Confidence: {p['confidence']}/10\n- Test stake: {p['stake_kr']} kr\n- Sport: {p['sport']}\n- Start: {p['commence_time']}\n- Mode: {p['mode']}\n\n")
print(summary)
