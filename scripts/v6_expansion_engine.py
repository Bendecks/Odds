import os, json, pathlib, requests, statistics, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)

ODDS_IO = os.getenv('ODDS_API_IO_KEY', '')
DISPLAY_TZ = os.getenv('DISPLAY_TZ', 'Europe/Copenhagen')
MAX_HOURS = int(os.getenv('MAX_HOURS', '36'))
MAX_TOP_BETS = int(os.getenv('MAX_TOP_BETS', '8'))
MODE = 'V18_EDGE_FILTER_ENGINE_SLUG_FIX'

# Canonical quality leagues. We match by slug/name aliases instead of exact guessed slug only.
LEAGUE_PATTERNS = [
    ('england-premier-league', ['premier', 'england']),
    ('spain-laliga', ['laliga', 'la-liga', 'spain', 'primera']),
    ('germany-bundesliga', ['bundesliga', 'germany']),
    ('italy-serie-a', ['serie-a', 'seriea', 'italy']),
    ('france-ligue-1', ['ligue-1', 'ligue1', 'france']),
    ('netherlands-eredivisie', ['eredivisie', 'netherlands', 'holland']),
    ('portugal-primeira-liga', ['primeira', 'portugal']),
    ('uefa-champions-league', ['champions-league', 'championsleague', 'uefa-champions']),
]

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
    'odds_errors': 0,
    'engine_note': 'Slug fix: allowed leagues are matched by slug/name aliases, with diagnostics.'
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
        return str(v)
    return d.astimezone(ZoneInfo(DISPLAY_TZ)).strftime('%Y-%m-%d %H:%M')


def odds_get(path, params=None):
    if not ODDS_IO:
        return []
    try:
        p = dict(params or {})
        p['apiKey'] = ODDS_IO
        r = requests.get('https://api.odds-api.io/v3' + path, params=p, timeout=40)
        if r.ok:
            return r.json()
        DIAG['odds_errors'] += 1
    except Exception:
        DIAG['odds_errors'] += 1
    return []


def league_identity(row):
    bits = [row.get('slug'), row.get('name'), row.get('title'), row.get('key'), row.get('id')]
    return ' '.join(norm(x) for x in bits if x)


def canonical_league(row):
    text = league_identity(row)
    slug = norm(row.get('slug'))

    for canonical, aliases in LEAGUE_PATTERNS:
        if slug == canonical:
            return canonical
        for a in aliases:
            a = norm(a)
            if a and a in text:
                return canonical
    return ''


def selected_leagues(raw_leagues):
    selected = []
    seen = set()
    DIAG['leagues_total'] = len(raw_leagues) if isinstance(raw_leagues, list) else 0

    for lg in raw_leagues if isinstance(raw_leagues, list) else []:
        if len(DIAG['league_samples']) < 30:
            DIAG['league_samples'].append({
                'slug': lg.get('slug'),
                'name': lg.get('name') or lg.get('title'),
                'eventsCount': lg.get('eventsCount')
            })

        canonical = canonical_league(lg)
        slug = lg.get('slug')
        if not canonical or not slug:
            DIAG['league_filtered'] += 1
            continue

        if canonical in seen:
            DIAG['league_filtered'] += 1
            continue

        seen.add(canonical)
        selected.append({'slug': slug, 'canonical': canonical, 'name': lg.get('name') or lg.get('title')})

    DIAG['leagues_selected'] = selected
    return selected


def extract_books(books, home, away):
    selections = {}

    if isinstance(books, list):
        converted = {}
        for row in books:
            if isinstance(row, dict):
                key = row.get('key') or row.get('name') or row.get('bookmaker') or 'book'
                converted[key] = row.get('markets') or row.get('odds') or []
        books = converted

    if not isinstance(books, dict):
        return selections

    for _, rows in books.items():
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            name = str(row.get('name') or row.get('key') or '').lower()
            if name not in ('h2h', 'ml', 'moneyline'):
                continue

            odds_rows = row.get('odds') or row.get('outcomes') or []
            if odds_rows and isinstance(odds_rows[0], dict) and any(k in odds_rows[0] for k in ('home', 'away', 'draw')):
                x = odds_rows[0]
                odds_rows = []
                if x.get('home') is not None:
                    odds_rows.append({'name': home, 'price': x.get('home')})
                if x.get('away') is not None:
                    odds_rows.append({'name': away, 'price': x.get('away')})

            for o in odds_rows:
                if not isinstance(o, dict):
                    continue
                sel = o.get('name') or o.get('label')
                pr = o.get('price') or o.get('odds')
                if not sel or str(sel).lower() == 'draw':
                    continue
                try:
                    pr = float(pr)
                except Exception:
                    continue
                if 1.30 <= pr <= 8:
                    selections.setdefault(sel, []).append(pr)

    return selections


def fetch_games():
    out = []
    leagues = selected_leagues(odds_get('/leagues', {'sport': 'football'}))

    for lg in leagues:
        events = odds_get('/events', {'sport': 'football', 'league': lg['slug']})
        if not isinstance(events, list):
            continue
        DIAG['event_count'] += len(events)

        for ev in events:
            if not isinstance(ev, dict) or not upcoming(ev.get('date')):
                continue
            DIAG['upcoming_event_count'] += 1

            oid = ev.get('id')
            if not oid:
                continue
            odds = odds_get('/odds', {'eventId': oid})
            if isinstance(odds, list):
                odds = odds[0] if odds and isinstance(odds[0], dict) else {}
            if not isinstance(odds, dict):
                continue

            home = odds.get('home') or ev.get('home')
            away = odds.get('away') or ev.get('away')
            books = odds.get('bookmakers') or {}
            selections = extract_books(books, home, away)

            for sel, vals in selections.items():
                vals = sorted(vals)
                if len(vals) < 3:
                    continue

                best = max(vals)
                median = statistics.median(vals)
                edge = ((best - median) / median) * 100 if median else 0

                if edge < 1.5:
                    DIAG['edge_filtered'] += 1
                    continue

                score = round(edge + (len(vals) * 0.15), 2)
                out.append({
                    'event': f'{home} vs {away}',
                    'event_id': oid,
                    'league': lg['canonical'],
                    'source_league_slug': lg['slug'],
                    'start': ev.get('date'),
                    'start_local': fmt(ev.get('date')),
                    'market': 'h2h',
                    'pick': sel,
                    'odds': round(best, 2),
                    'median_odds': round(median, 2),
                    'edge_pct': round(edge, 2),
                    'books': len(vals),
                    'pre_score': score,
                    'confidence': 'real_market_edge',
                    'sport': 'soccer_odds_api_io',
                    'sport_bucket': 'soccer'
                })

    return out


def dedupe(cands):
    out = []
    seen = set()
    for c in sorted(cands, key=lambda x: x['pre_score'], reverse=True):
        key = c.get('event_id')
        if key in seen:
            DIAG['duplicates_removed'] += 1
            continue
        seen.add(key)
        out.append(c)
    return out


def rank(cands):
    cands = dedupe(cands)
    approved = [
        c for c in cands
        if c['edge_pct'] >= 1.5
        and c['books'] >= 3
        and 1.50 <= c['odds'] <= 2.40
    ]
    approved = sorted(approved, key=lambda x: (x['edge_pct'], x['books'], x['pre_score']), reverse=True)
    top = approved[:MAX_TOP_BETS]

    for t in top:
        t['role'] = 'PRIMARY'
        t['stake_kr'] = max(10, round(t['edge_pct'] * 4))
        t['reason'] = f"Reel market edge på {t['edge_pct']}% mod medianodds. Valideret af {t['books']} bookmaker-priser."

    DIAG['top_count'] = len(top)
    return {
        'summary': ('ingen valide bets' if not top else f'{len(top)} edge bets'),
        'top_bets': top,
        'watchlist': [],
        'pass': []
    }


cands = fetch_games()
DIAG['candidate_count'] = len(cands)
res = rank(cands)
res['mode'] = MODE
res['generated_at'] = now_iso()
res['diagnostics'] = DIAG

(OUT / 'v6_expansion_engine.json').write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')

with open(OUT / 'v6_expansion_engine.md', 'w', encoding='utf-8') as f:
    f.write(f"# {MODE}\n\n{res['summary']}\n\n")
    f.write('## DIAGNOSTICS\n```json\n' + json.dumps(DIAG, ensure_ascii=False, indent=2) + '\n```\n\n')
    for i, x in enumerate(res['top_bets'], 1):
        f.write(
            f"{i}. {x['start_local']}\n"
            f"Liga: {x['league']} ({x.get('source_league_slug')})\n"
            f"Kamp: {x['event']}\n"
            f"Spil: Vinder = {x['pick']}\n"
            f"Odds: {x['odds']}\n"
            f"Medianodds: {x['median_odds']}\n"
            f"Market edge: {x['edge_pct']}%\n"
            f"Bookmakers: {x['books']}\n"
            f"Stake: {x['stake_kr']} kr\n"
            f"Forklaring: {x['reason']}\n\n"
        )

print(res['summary'])
