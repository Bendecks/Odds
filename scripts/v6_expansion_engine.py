import os, json, pathlib, requests, statistics
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)

THE_ODDS = os.getenv('THE_ODDS_API_KEY', '')
ODDS_IO = os.getenv('ODDS_API_IO_KEY', '')
DISPLAY_TZ = os.getenv('DISPLAY_TZ', 'Europe/Copenhagen')
MAX_HOURS = int(os.getenv('MAX_HOURS', '36'))
MAX_TOP_BETS = int(os.getenv('MAX_TOP_BETS', '20'))
ODDS_IO_BOOKMAKER = os.getenv('ODDS_API_IO_BOOKMAKER', '1xbet')
ODDS_IO_MAX_EVENTS = int(os.getenv('ODDS_API_IO_MAX_EVENTS', '25'))
ODDS_IO_SPORTS = os.getenv('ODDS_IO_SPORTS', 'football').split(',')
THEODDS_SPORTS = os.getenv('THEODDS_SPORTS', 'soccer_epl,soccer_spain_la_liga,soccer_germany_bundesliga,soccer_italy_serie_a,soccer_france_ligue_one,soccer_netherlands_eredivisie,soccer_portugal_primeira_liga,soccer_turkey_super_league,soccer_belgium_first_div,soccer_denmark_superliga,soccer_uefa_champs_league,soccer_uefa_europa_league').split(',')
MARKETS = ('h2h',)
MODE = 'V14_FOOTBALL_ONLY_NEAR_TERM_ENGINE'

DIAG = {
    'api_errors': [],
    'quota_exhausted': False,
    'max_hours': MAX_HOURS,
    'theodds_games': 0,
    'odds_api_io_events': 0,
    'odds_api_io_games': 0,
    'candidate_count': 0,
    'top_count': 0,
    'odds_io_leagues_used': [],
    'engine_note': 'Football-only near-term engine. Non-football is not fetched while Strict Mode is football-only.'
}


def now_iso(): return datetime.now(timezone.utc).isoformat()
def as_list(v): return v if isinstance(v, list) else []
def first_dict(v):
    if isinstance(v, dict): return v
    if isinstance(v, list):
        for x in v:
            if isinstance(x, dict): return x
    return {}

def parse_dt(v):
    try: return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except Exception: return None

def upcoming(v):
    d = parse_dt(v)
    if not d: return False
    hours = (d - datetime.now(timezone.utc)).total_seconds() / 3600
    return 0 < hours <= MAX_HOURS

def fmt_start(v):
    d = parse_dt(v)
    if not d: return str(v or '')
    return d.astimezone(ZoneInfo(DISPLAY_TZ)).strftime('%Y-%m-%d %H:%M')

def mark_error(label, err):
    txt = str(err)[:700]
    if 'OUT_OF_USAGE_CREDITS' in txt or 'Usage quota' in txt: DIAG['quota_exhausted'] = True
    DIAG['api_errors'].append({'label': label, 'error': txt})

def safe_get(label, url, params=None):
    try:
        r = requests.get(url, params=params or {}, timeout=45)
        if not r.ok: raise RuntimeError(f'{r.status_code} {r.text[:500]}')
        return r.json()
    except Exception as e:
        mark_error(label, e)
        return []

def fetch_theodds():
    if not THE_ODDS: return []
    games = []
    for sport in [s.strip() for s in THEODDS_SPORTS if s.strip()]:
        data = safe_get('theodds:' + sport, f'https://api.the-odds-api.com/v4/sports/{sport}/odds', {
            'apiKey': THE_ODDS, 'regions': 'eu,uk', 'markets': ','.join(MARKETS), 'oddsFormat': 'decimal'
        })
        if isinstance(data, list):
            for g in data:
                if isinstance(g, dict) and upcoming(g.get('commence_time')):
                    g['source'] = 'the-odds-api'
                    games.append(g)
    DIAG['theodds_games'] = len(games)
    return games

def odds_io_get(path, params=None):
    if not ODDS_IO: return []
    p = dict(params or {})
    p['apiKey'] = ODDS_IO
    return safe_get('odds-api.io:' + path, 'https://api.odds-api.io/v3' + path, p)

def odds_io_pick_leagues():
    preferred = ['england-premier-league','spain-laliga','germany-bundesliga','italy-serie-a','france-ligue-1','netherlands-eredivisie','portugal-primeira-liga','turkey-super-lig','belgium-first-division-a','denmark-superliga']
    leagues = odds_io_get('/leagues', {'sport': 'football'})
    if not isinstance(leagues, list): leagues = []
    by_slug = {x.get('slug'): x for x in leagues if isinstance(x, dict) and x.get('slug')}
    out = [s for s in preferred if s in by_slug and int(by_slug[s].get('eventsCount') or 0) > 0]
    rows = [x for x in leagues if isinstance(x, dict) and x.get('slug') and int(x.get('eventsCount') or 0) > 0]
    rows = sorted(rows, key=lambda x: int(x.get('eventsCount') or 0), reverse=True)
    for row in rows:
        slug = row.get('slug')
        if slug not in out:
            out.append(slug)
        if len(out) >= 10:
            break
    DIAG['odds_io_leagues_used'] = out
    return out

def odds_io_markets(raw_odds, home, away):
    odds = first_dict(raw_odds)
    if not odds: return []
    bobj = odds.get('bookmakers')
    if isinstance(bobj, list):
        converted = {}
        for row in bobj:
            if isinstance(row, dict):
                key = row.get('key') or row.get('name') or row.get('bookmaker') or 'book'
                converted[key] = row.get('markets') or row.get('odds') or []
        bobj = converted
    if not isinstance(bobj, dict): return []
    books = []
    for bookmaker, rows in bobj.items():
        markets = []
        for m in rows if isinstance(rows, list) else []:
            if not isinstance(m, dict): continue
            name = str(m.get('name') or m.get('key') or '').lower()
            if name not in ('ml', 'h2h', 'moneyline'): continue
            odds_rows = m.get('odds') or m.get('outcomes') or []
            outs = []
            if odds_rows and isinstance(odds_rows[0], dict) and any(k in odds_rows[0] for k in ('home', 'away', 'draw')):
                row = odds_rows[0]
                if row.get('home') is not None: outs.append({'name': home, 'price': row.get('home')})
                if row.get('away') is not None: outs.append({'name': away, 'price': row.get('away')})
            else:
                for row in odds_rows:
                    if isinstance(row, dict):
                        nm = row.get('name') or row.get('label')
                        pr = row.get('price') or row.get('odds')
                        if nm and str(nm).lower() != 'draw': outs.append({'name': nm, 'price': pr})
            if outs: markets.append({'key': 'h2h', 'outcomes': outs})
        if markets: books.append({'key': bookmaker, 'markets': markets})
    return books

def fetch_odds_io():
    if not ODDS_IO: return []
    games = []
    for league in odds_io_pick_leagues():
        events = odds_io_get('/events', {'sport': 'football', 'league': league})
        if not isinstance(events, list): events = []
        DIAG['odds_api_io_events'] += len(events)
        near_events = [ev for ev in events if isinstance(ev, dict) and upcoming(ev.get('date'))]
        for ev in near_events[:ODDS_IO_MAX_EVENTS]:
            oid = ev.get('id')
            if not oid: continue
            raw_odds = odds_io_get('/odds', {'eventId': oid, 'bookmakers': ODDS_IO_BOOKMAKER})
            odds = first_dict(raw_odds)
            home = odds.get('home') or ev.get('home')
            away = odds.get('away') or ev.get('away')
            books = odds_io_markets(raw_odds, home, away)
            if not home or not away or not books: continue
            games.append({'id': 'oddsio_' + str(oid), 'source': 'odds-api.io', 'sport_key': 'soccer_odds_api_io', 'home_team': home, 'away_team': away, 'commence_time': odds.get('date') or ev.get('date'), 'bookmakers': books})
    DIAG['odds_api_io_games'] = len(games)
    return games

def add_candidate(cands, g, market, selection, prices):
    vals = []
    for p in prices:
        try:
            fp = float(p)
            if 1.2 <= fp <= 8: vals.append(fp)
        except Exception: pass
    if not vals: return
    best = max(vals)
    med = statistics.median(vals)
    books = len(vals)
    single_source = books < 2
    edge = 0.0 if single_source else (best / med - 1 if med else 0.0)
    if single_source:
        score = 7.2 if 1.50 <= best <= 2.50 else 4.0
        confidence = 'controlled_single_source'
    else:
        score = edge * 100 + 3 + (2 if books >= 20 else 1 if books >= 8 else 0)
        confidence = 'market_consensus'
    if best >= 3: score -= 2
    if score < 5.5: return
    cands.append({'event': f"{g.get('home_team')} vs {g.get('away_team')}", 'event_id': g.get('id'), 'source': g.get('source') or 'unknown', 'sport': g.get('sport_key'), 'sport_bucket': 'soccer', 'start': g.get('commence_time'), 'start_local': fmt_start(g.get('commence_time')), 'market': market, 'selection': selection, 'point': None, 'odds': round(best, 2), 'median': round(med, 2), 'edge_pct': round(edge * 100, 1), 'books': books, 'pre_score': round(score, 2), 'confidence': confidence, 'single_source': single_source})

def parse_games(games):
    cands = []
    for g in games:
        buckets = {}
        for b in as_list(g.get('bookmakers')):
            if not isinstance(b, dict): continue
            for m in as_list(b.get('markets')):
                if not isinstance(m, dict) or m.get('key') != 'h2h': continue
                for o in as_list(m.get('outcomes')):
                    if not isinstance(o, dict): continue
                    name = o.get('name')
                    if str(name).lower() == 'draw': continue
                    buckets.setdefault(('h2h', name), []).append(o.get('price'))
        for (mk, name), prices in buckets.items(): add_candidate(cands, g, mk, name, prices)
    DIAG['candidate_count'] = len(cands)
    return sorted(cands, key=lambda x: (x['pre_score'], x['books'], x['odds']), reverse=True)

def collect_candidates():
    games = fetch_theodds() + fetch_odds_io()
    seen = set(); uniq = []
    for g in games:
        key = (g.get('id'), g.get('sport_key'), g.get('home_team'), g.get('away_team'), g.get('commence_time'))
        if str(key) in seen: continue
        seen.add(str(key)); uniq.append(g)
    return parse_games(uniq)

def top_eligible(c):
    odds = float(c.get('odds') or 0); score = float(c.get('pre_score') or 0)
    return 1.50 <= odds <= 2.50 and score >= 7.0

def conflicts(a, b):
    return a.get('event') == b.get('event')

def rank(cands):
    top = []; watch = []
    for c in cands:
        item = {'event': c['event'], 'event_id': c.get('event_id'), 'source': c.get('source'), 'sport': c.get('sport'), 'sport_bucket': c.get('sport_bucket'), 'start': c.get('start'), 'start_local': c.get('start_local'), 'market': c.get('market'), 'pick': c.get('selection'), 'point': c.get('point'), 'odds': c.get('odds'), 'edge_pct': c.get('edge_pct'), 'books': c.get('books'), 'pre_score': c.get('pre_score'), 'confidence': c.get('confidence'), 'single_source': c.get('single_source')}
        if not top_eligible(c): item['role'] = 'WATCHLIST'; item['stake_kr'] = 0; item['reason'] = 'Ikke indenfor Strict V2.1.'; watch.append(item); continue
        if any(conflicts(c, t) for t in top): item['role'] = 'WATCHLIST'; item['stake_kr'] = 0; item['reason'] = 'Kun 1 bet pr kamp.'; watch.append(item); continue
        item['role'] = 'PRIMARY'; item['stake_kr'] = 1; item['reason'] = 'Football-only Strict V2.1 candidate.'
        top.append(item)
        if len(top) >= MAX_TOP_BETS: break
    DIAG['top_count'] = len(top)
    return {'summary': ('ingen spil nu' if not top else f'{len(top)} top bets'), 'top_bets': top, 'watchlist': watch[:80], 'pass': []}

cands = collect_candidates(); res = rank(cands)
if DIAG.get('quota_exhausted'): res['summary'] = 'THE_ODDS_API quota brugt. ' + res['summary'] + ' (odds-api.io fallback aktiv)'
res['mode'] = MODE; res['generated_at'] = now_iso(); res['candidate_count'] = len(cands); res['diagnostics'] = DIAG
(OUT / 'v6_expansion_engine.json').write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
with open(OUT / 'v6_expansion_engine.md', 'w', encoding='utf-8') as f:
    f.write(f"# {MODE}\n\n{res['summary']}\n\n")
    f.write('## DIAGNOSTICS\n```json\n' + json.dumps(DIAG, ensure_ascii=False, indent=2) + '\n```\n\n')
    for sec in ['top_bets', 'watchlist', 'pass']:
        f.write('## ' + sec.upper() + '\n')
        for i, x in enumerate(as_list(res.get(sec)), 1):
            f.write(f"{i}. {x.get('start_local')} | {x.get('event')} | {x.get('market')} | {x.get('pick')} | odds {x.get('odds')} | units {x.get('stake_kr')} | source {x.get('source')} | conf {x.get('confidence')} | score {x.get('pre_score')} | {x.get('reason')}\n")
        f.write('\n')
print(res['summary'])
