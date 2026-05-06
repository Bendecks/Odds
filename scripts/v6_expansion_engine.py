import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)

ENGINE_JSON = OUT / 'v6_expansion_engine.json'
ENGINE_MD = OUT / 'v6_expansion_engine.md'
DEBUG_JSON = OUT / 'odds_candidate_debug.json'

ODDS_IO = os.getenv('ODDS_API_IO_KEY', '')
DISPLAY_TZ = os.getenv('DISPLAY_TZ', 'Europe/Copenhagen')
MAX_HOURS = int(os.getenv('MAX_HOURS', '72'))
MAX_TOP_BETS = int(os.getenv('MAX_TOP_BETS', '8'))
MIN_BOOK_PRICES = int(os.getenv('MIN_BOOK_PRICES', '3'))
MIN_EDGE_PCT = float(os.getenv('MIN_EDGE_PCT', '1.5'))
MIN_ODDS = float(os.getenv('MIN_ODDS', '1.50'))
MAX_ODDS = float(os.getenv('MAX_ODDS', '2.40'))
ODDS_IO_BOOKMAKERS = os.getenv('ODDS_IO_BOOKMAKERS', '1xbet')
MODE = 'V18_EXACT_LEAGUE_EDGE_ENGINE_ODDS_FALLBACK'

APPROVED_LEAGUES = {
    'england-premier-league': 'england-premier-league',
    'spain-laliga': 'spain-laliga',
    'germany-bundesliga': 'germany-bundesliga',
    'italy-serie-a': 'italy-serie-a',
    'france-ligue-1': 'france-ligue-1',
    'netherlands-eredivisie': 'netherlands-eredivisie',
    'portugal-primeira-liga': 'portugal-primeira-liga',
    'international-clubs-uefa-champions-league': 'uefa-champions-league',
    'uefa-champions-league': 'uefa-champions-league',
}

DIAG = {
    'candidate_count': 0,
    'top_count': 0,
    'duplicates_removed': 0,
    'edge_filtered': 0,
    'league_filtered': 0,
    'leagues_total': 0,
    'leagues_selected': [],
    'league_samples': [],
    'event_count': 0,
    'upcoming_event_count': 0,
    'odds_events_checked': 0,
    'odds_errors': 0,
    'odds_successes': 0,
    'odds_fallback_attempts': 0,
    'odds_error_samples': [],
    'odds_success_pattern': {},
    'markets_found': 0,
    'rejected_short_prices': 0,
    'rejected_odds_range': 0,
    'api_key_present': bool(ODDS_IO),
    'bookmakers_param': ODDS_IO_BOOKMAKERS,
    'engine_note': 'Exact approved league slugs. Odds endpoint now tries several endpoint/parameter patterns and logs failures.'
}

DEBUG = {
    'generated_at': None,
    'selected_leagues': [],
    'upcoming_events': [],
    'candidate_rows': [],
    'rejected_rows': [],
    'odds_error_samples': [],
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def norm(s):
    return re.sub(r'[^a-z0-9]+', '-', str(s or '').lower()).strip('-')


def parse_dt(v):
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except Exception:
        return None


def upcoming(v):
    d = parse_dt(v)
    if not d:
        return False
    h = (d - datetime.now(timezone.utc)).total_seconds() / 3600
    return 0 < h <= MAX_HOURS


def fmt(v):
    d = parse_dt(v)
    if not d:
        return str(v or '')
    return d.astimezone(ZoneInfo(DISPLAY_TZ)).strftime('%Y-%m-%d %H:%M')


def add_limited(collection, row, max_len=250):
    if len(collection) < max_len:
        collection.append(row)


def request_json(path, params=None, label=''):
    if not ODDS_IO:
        return None, 'missing_api_key'
    p = dict(params or {})
    p['apiKey'] = ODDS_IO
    url = 'https://api.odds-api.io/v3' + path
    try:
        r = requests.get(url, params=p, timeout=45)
        if r.ok:
            return r.json(), ''
        return None, f'{r.status_code} {r.text[:240]}'
    except Exception as e:
        return None, str(e)[:240]


def odds_get(path, params=None):
    data, err = request_json(path, params, path)
    if err:
        DIAG['odds_errors'] += 1
        add_limited(DIAG['odds_error_samples'], {'path': path, 'params': {k: v for k, v in (params or {}).items() if k != 'apiKey'}, 'error': err}, 20)
    return data if data is not None else []


def fetch_event_odds(event_id):
    # odds-api.io has changed/varied endpoint parameter names across examples.
    # Try safest patterns in a fixed order. First pattern uses bookmaker(s), because /odds often rejects bare eventId.
    patterns = [
        ('/odds', {'eventId': event_id, 'bookmakers': ODDS_IO_BOOKMAKERS}, 'odds_eventId_bookmakers'),
        ('/odds', {'eventId': event_id, 'bookmaker': ODDS_IO_BOOKMAKERS}, 'odds_eventId_bookmaker'),
        ('/odds', {'eventId': event_id}, 'odds_eventId'),
        ('/odds', {'event_id': event_id, 'bookmakers': ODDS_IO_BOOKMAKERS}, 'odds_event_id_bookmakers'),
        ('/odds', {'event_id': event_id}, 'odds_event_id'),
        ('/odds', {'id': event_id, 'bookmakers': ODDS_IO_BOOKMAKERS}, 'odds_id_bookmakers'),
        (f'/events/{event_id}/odds', {'bookmakers': ODDS_IO_BOOKMAKERS}, 'events_id_odds_bookmakers'),
        (f'/odds/{event_id}', {'bookmakers': ODDS_IO_BOOKMAKERS}, 'odds_id_path_bookmakers'),
    ]

    errors = []
    for path, params, label in patterns:
        DIAG['odds_fallback_attempts'] += 1
        data, err = request_json(path, params, label)
        if not err and data not in (None, [], {}):
            DIAG['odds_successes'] += 1
            DIAG['odds_success_pattern'][label] = DIAG['odds_success_pattern'].get(label, 0) + 1
            return data
        if err:
            errors.append({'pattern': label, 'error': err})

    DIAG['odds_errors'] += 1
    sample = {'event_id': event_id, 'errors': errors[:4]}
    add_limited(DIAG['odds_error_samples'], sample, 20)
    add_limited(DEBUG['odds_error_samples'], sample, 50)
    return {}


def selected_leagues(raw_leagues):
    selected = []
    DIAG['leagues_total'] = len(raw_leagues) if isinstance(raw_leagues, list) else 0
    for lg in raw_leagues if isinstance(raw_leagues, list) else []:
        if not isinstance(lg, dict):
            continue
        slug = norm(lg.get('slug'))
        name = lg.get('name') or lg.get('title')
        if len(DIAG['league_samples']) < 100:
            DIAG['league_samples'].append({'slug': lg.get('slug'), 'name': name, 'eventsCount': lg.get('eventsCount')})
        canonical = APPROVED_LEAGUES.get(slug)
        if not canonical:
            DIAG['league_filtered'] += 1
            continue
        selected.append({'slug': lg.get('slug'), 'canonical': canonical, 'name': name, 'eventsCount': lg.get('eventsCount')})
    DIAG['leagues_selected'] = selected
    DEBUG['selected_leagues'] = selected
    return selected


def extract_prices_from_bookmakers(bookmakers, home, away):
    selections = {}
    if isinstance(bookmakers, list):
        converted = {}
        for row in bookmakers:
            if isinstance(row, dict):
                key = row.get('key') or row.get('name') or row.get('bookmaker') or f'book_{len(converted)+1}'
                converted[key] = row.get('markets') or row.get('odds') or []
        bookmakers = converted
    if not isinstance(bookmakers, dict):
        return selections

    for _, rows in bookmakers.items():
        for market in rows if isinstance(rows, list) else []:
            if not isinstance(market, dict):
                continue
            market_name = str(market.get('name') or market.get('key') or '').lower()
            if market_name not in ('h2h', 'ml', 'moneyline'):
                continue
            DIAG['markets_found'] += 1
            outcomes = market.get('odds') or market.get('outcomes') or []
            if outcomes and isinstance(outcomes[0], dict) and any(k in outcomes[0] for k in ('home', 'away', 'draw')):
                row = outcomes[0]
                outcomes = []
                if row.get('home') is not None:
                    outcomes.append({'name': home, 'price': row.get('home')})
                if row.get('away') is not None:
                    outcomes.append({'name': away, 'price': row.get('away')})
            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    continue
                name = outcome.get('name') or outcome.get('label')
                price = outcome.get('price') or outcome.get('odds')
                if not name or str(name).lower() == 'draw':
                    continue
                try:
                    price = float(price)
                except Exception:
                    continue
                if 1.30 <= price <= 8:
                    selections.setdefault(str(name), []).append(price)
    return selections


def normalize_odds_payload(payload):
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                return item
        return {}
    return payload if isinstance(payload, dict) else {}


def fetch_candidates():
    candidates = []
    leagues = selected_leagues(odds_get('/leagues', {'sport': 'football'}))
    for league in leagues:
        events = odds_get('/events', {'sport': 'football', 'league': league['slug']})
        if not isinstance(events, list):
            continue
        DIAG['event_count'] += len(events)
        for event in events:
            if not isinstance(event, dict) or not upcoming(event.get('date')):
                continue
            DIAG['upcoming_event_count'] += 1
            event_id = event.get('id')
            home_hint = event.get('home')
            away_hint = event.get('away')
            add_limited(DEBUG['upcoming_events'], {'league': league['canonical'], 'source_league_slug': league['slug'], 'event_id': event_id, 'date': event.get('date'), 'home': home_hint, 'away': away_hint})
            if not event_id:
                continue
            DIAG['odds_events_checked'] += 1
            odds = normalize_odds_payload(fetch_event_odds(event_id))
            if not odds:
                continue
            home = odds.get('home') or home_hint
            away = odds.get('away') or away_hint
            selections = extract_prices_from_bookmakers(odds.get('bookmakers') or {}, home, away)
            for selection, prices in selections.items():
                clean_prices = []
                for p in prices:
                    try:
                        clean_prices.append(float(p))
                    except Exception:
                        pass
                clean_prices = sorted(clean_prices)
                if len(clean_prices) < MIN_BOOK_PRICES:
                    DIAG['rejected_short_prices'] += 1
                    add_limited(DEBUG['rejected_rows'], {'event': f'{home} vs {away}', 'pick': selection, 'reason': 'too_few_prices', 'prices': len(clean_prices)})
                    continue
                best = max(clean_prices)
                median = statistics.median(clean_prices)
                edge = ((best - median) / median) * 100 if median else 0.0
                row = {'event': f'{home} vs {away}', 'event_id': event_id, 'league': league['canonical'], 'source_league_slug': league['slug'], 'start': event.get('date'), 'start_local': fmt(event.get('date')), 'market': 'h2h', 'pick': selection, 'odds': round(best, 2), 'median_odds': round(median, 2), 'edge_pct': round(edge, 2), 'books': len(clean_prices), 'pre_score': round(edge + len(clean_prices) * 0.15, 2), 'confidence': 'real_market_edge', 'sport': 'soccer_odds_api_io', 'sport_bucket': 'soccer'}
                add_limited(DEBUG['candidate_rows'], row)
                if edge < MIN_EDGE_PCT:
                    DIAG['edge_filtered'] += 1
                    add_limited(DEBUG['rejected_rows'], {**row, 'reason': 'edge_below_minimum'})
                    continue
                if not (MIN_ODDS <= best <= MAX_ODDS):
                    DIAG['rejected_odds_range'] += 1
                    add_limited(DEBUG['rejected_rows'], {**row, 'reason': 'odds_outside_range'})
                    continue
                candidates.append(row)
    return candidates


def dedupe(candidates):
    result = []
    seen = set()
    for item in sorted(candidates, key=lambda x: (x['pre_score'], x['edge_pct'], x['books']), reverse=True):
        key = item.get('event_id')
        if key in seen:
            DIAG['duplicates_removed'] += 1
            continue
        seen.add(key)
        result.append(item)
    return result


def rank(candidates):
    approved = sorted(dedupe(candidates), key=lambda x: (x['edge_pct'], x['books'], x['pre_score']), reverse=True)
    top = approved[:MAX_TOP_BETS]
    for item in top:
        item['role'] = 'PRIMARY_V18'
        item['stake_kr'] = max(10, round(item['edge_pct'] * 4))
        item['reason'] = f"Reel market edge på {item['edge_pct']}% mod medianodds. Valideret af {item['books']} bookmaker-priser."
    DIAG['candidate_count'] = len(candidates)
    DIAG['top_count'] = len(top)
    return {'summary': ('ingen valide bets' if not top else f'{len(top)} edge bets'), 'top_bets': top, 'watchlist': [], 'pass': []}


def write_md(result):
    lines = [f'# {MODE}', '', result.get('summary', ''), '', '## DIAGNOSTICS', '```json', json.dumps(DIAG, ensure_ascii=False, indent=2), '```', '', '## TOP BETS']
    if not result.get('top_bets'):
        lines.append('Ingen valide bets fundet i dette run.')
    for i, item in enumerate(result.get('top_bets') or [], 1):
        lines.extend([f'{i}. {item.get("start_local")}', f'Liga: {item.get("league")} ({item.get("source_league_slug")})', f'Kamp: {item.get("event")}', f'Spil: Vinder = {item.get("pick")}', f'Odds: {item.get("odds")}', f'Medianodds: {item.get("median_odds")}', f'Market edge: {item.get("edge_pct")}% ', f'Bookmakers: {item.get("books")}', f'Stake: {item.get("stake_kr")} kr', f'Forklaring: {item.get("reason")}', ''])
    ENGINE_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    candidates = fetch_candidates()
    result = rank(candidates)
    result['mode'] = MODE
    result['generated_at'] = now_iso()
    result['diagnostics'] = DIAG
    DEBUG['generated_at'] = result['generated_at']
    DEBUG_JSON.write_text(json.dumps(DEBUG, ensure_ascii=False, indent=2), encoding='utf-8')
    ENGINE_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    write_md(result)
    print(result['summary'])


if __name__ == '__main__':
    main()
