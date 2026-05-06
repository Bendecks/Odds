import os, json, pathlib, requests, statistics
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)

ODDS_IO = os.getenv('ODDS_API_IO_KEY', '')
DISPLAY_TZ = os.getenv('DISPLAY_TZ', 'Europe/Copenhagen')
MAX_HOURS = int(os.getenv('MAX_HOURS', '36'))
MAX_TOP_BETS = int(os.getenv('MAX_TOP_BETS', '8'))
MODE = 'V18_EDGE_FILTER_ENGINE'

GOOD_LEAGUES = {
    'england-premier-league',
    'spain-laliga',
    'germany-bundesliga',
    'italy-serie-a',
    'france-ligue-1',
    'netherlands-eredivisie',
    'portugal-primeira-liga',
    'uefa-champions-league'
}

DIAG = {
    'candidate_count': 0,
    'top_count': 0,
    'duplicates_removed': 0,
    'edge_filtered': 0,
    'league_filtered': 0,
    'engine_note': 'Real edge scoring + hard dedupe + stronger league filtering'
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


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
    except Exception:
        pass
    return []


def fetch_games():
    out = []
    leagues = odds_get('/leagues', {'sport': 'football'})

    for lg in leagues if isinstance(leagues, list) else []:
        slug = lg.get('slug')
        if slug not in GOOD_LEAGUES:
            DIAG['league_filtered'] += 1
            continue

        events = odds_get('/events', {'sport': 'football', 'league': slug})

        for ev in events if isinstance(events, list) else []:
            if not upcoming(ev.get('date')):
                continue

            oid = ev.get('id')
            odds = odds_get('/odds', {'eventId': oid})

            if isinstance(odds, list):
                odds = odds[0] if odds and isinstance(odds[0], dict) else {}

            books = odds.get('bookmakers') or {}
            if not isinstance(books, dict):
                continue

            home = odds.get('home') or ev.get('home')
            away = odds.get('away') or ev.get('away')

            selections = {}

            for _, rows in books.items():
                for row in rows if isinstance(rows, list) else []:
                    name = str(row.get('name') or '').lower()
                    if name not in ('h2h', 'ml', 'moneyline'):
                        continue

                    for o in row.get('odds', []):
                        if not isinstance(o, dict):
                            continue

                        sel = o.get('name')
                        pr = o.get('price')

                        if not sel or str(sel).lower() == 'draw':
                            continue

                        try:
                            pr = float(pr)
                        except Exception:
                            continue

                        if 1.30 <= pr <= 8:
                            selections.setdefault(sel, []).append(pr)

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
                    'league': slug,
                    'start': ev.get('date'),
                    'start_local': fmt(ev.get('date')),
                    'market': 'h2h',
                    'pick': sel,
                    'odds': round(best, 2),
                    'median_odds': round(median, 2),
                    'edge_pct': round(edge, 2),
                    'books': len(vals),
                    'pre_score': score,
                    'confidence': 'real_market_edge'
                })

    return out


def dedupe(cands):
    out = []
    seen = {}

    for c in sorted(cands, key=lambda x: x['pre_score'], reverse=True):
        key = c['event_id']

        if key in seen:
            DIAG['duplicates_removed'] += 1
            continue

        seen[key] = True
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

    approved = sorted(
        approved,
        key=lambda x: (x['edge_pct'], x['books'], x['pre_score']),
        reverse=True
    )

    top = approved[:MAX_TOP_BETS]

    for t in top:
        t['role'] = 'PRIMARY'
        t['stake_kr'] = max(10, round(t['edge_pct'] * 4))
        t['reason'] = (
            f"Reel market edge på {t['edge_pct']}% mod medianodds. "
            f"Valideret af {t['books']} bookmaker-priser."
        )

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

(OUT / 'v6_expansion_engine.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=2),
    encoding='utf-8'
)

with open(OUT / 'v6_expansion_engine.md', 'w', encoding='utf-8') as f:
    f.write(f"# {MODE}\n\n{res['summary']}\n\n")

    for i, x in enumerate(res['top_bets'], 1):
        f.write(
            f"{i}. {x['start_local']}\n"
            f"Liga: {x['league']}\n"
            f"Kamp: {x['event']}\n"
            f"Spil: Vinder = {x['pick']}\n"
            f"Odds: {x['odds']}\n"
            f"Market edge: {x['edge_pct']}%\n"
            f"Bookmakers: {x['books']}\n"
            f"Stake: {x['stake_kr']} kr\n"
            f"Forklaring: {x['reason']}\n\n"
        )

print(res['summary'])
