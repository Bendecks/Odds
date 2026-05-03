import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
ENGINE_JSON = OUT / 'v6_expansion_engine.json'
ENGINE_MD = OUT / 'v6_expansion_engine.md'

STRICT_ALLOWED_SPORT_PREFIXES = (
    'soccer_epl',
    'soccer_spain_la_liga',
    'soccer_germany_bundesliga',
    'soccer_football_data',
)
STRICT_ALLOWED_ODDS_IO_SPORTS = (
    'soccer_odds_api_io',
)
STRICT_ALLOWED_MARKETS = ('h2h', 'totals')
STRICT_MAX_ODDS = 3.00
STRICT_MAX_TOP_BETS = 5
STRICT_MIN_SCORE = 6.0
STRICT_ALLOW_SINGLE_SOURCE = False


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def is_soccer_allowed(item):
    sport = str(item.get('sport') or '')
    if sport.startswith(STRICT_ALLOWED_SPORT_PREFIXES):
        return True
    if sport in STRICT_ALLOWED_ODDS_IO_SPORTS:
        return True
    return False


def rejection_reason(item):
    sport = str(item.get('sport') or '')
    market = str(item.get('market') or '').lower()
    try:
        odds = float(item.get('odds') or 0)
    except Exception:
        odds = 0.0
    try:
        score = float(item.get('pre_score') or 0)
    except Exception:
        score = 0.0

    if not is_soccer_allowed(item):
        return 'Strict Mode: kun fodboldligaer med god result dækning er tilladt.'
    if market not in STRICT_ALLOWED_MARKETS:
        return 'Strict Mode: spread/handicap er slået fra.'
    if odds <= 0 or odds > STRICT_MAX_ODDS:
        return f'Strict Mode: odds over {STRICT_MAX_ODDS} er slået fra.'
    if item.get('single_source') and not STRICT_ALLOW_SINGLE_SOURCE:
        return 'Strict Mode: single-source odds-api.io pick må ikke være top bet.'
    if score < STRICT_MIN_SCORE:
        return f'Strict Mode: score under {STRICT_MIN_SCORE}.'
    return ''


def normalize_watch(item, reason):
    item = dict(item)
    item['role'] = 'WATCHLIST'
    item['stake_kr'] = 0
    existing = str(item.get('reason') or '')
    item['reason'] = (existing + ' | ' if existing else '') + reason
    return item


def strict_filter(engine):
    old_top = engine.get('top_bets') if isinstance(engine.get('top_bets'), list) else []
    old_watch = engine.get('watchlist') if isinstance(engine.get('watchlist'), list) else []
    new_top = []
    moved = []
    seen_events = set()

    for item in old_top:
        if not isinstance(item, dict):
            continue
        reason = rejection_reason(item)
        event = str(item.get('event') or '')
        if event in seen_events:
            reason = 'Strict Mode: max 1 bet pr kamp.'
        if reason:
            moved.append(normalize_watch(item, reason))
            continue
        clean = dict(item)
        clean['role'] = 'PRIMARY_STRICT'
        clean['stake_kr'] = min(float(clean.get('stake_kr') or 1), 1)
        clean['strict_mode'] = True
        clean['reason'] = (str(clean.get('reason') or '') + ' | Strict Mode: godkendt, max 1 unit.').strip()
        new_top.append(clean)
        seen_events.add(event)
        if len(new_top) >= STRICT_MAX_TOP_BETS:
            break

    # Anything beyond max top bets becomes watchlist.
    for item in old_top:
        if isinstance(item, dict) and item not in new_top and item not in moved:
            moved.append(normalize_watch(item, f'Strict Mode: max {STRICT_MAX_TOP_BETS} top bets.'))

    engine['top_bets'] = new_top
    engine['watchlist'] = moved + old_watch
    engine['mode'] = str(engine.get('mode') or '') + '+STRICT_MODE'
    engine['strict_mode'] = {
        'activated_at': now_iso(),
        'allowed_sports': list(STRICT_ALLOWED_SPORT_PREFIXES) + list(STRICT_ALLOWED_ODDS_IO_SPORTS),
        'allowed_markets': list(STRICT_ALLOWED_MARKETS),
        'max_odds': STRICT_MAX_ODDS,
        'max_top_bets': STRICT_MAX_TOP_BETS,
        'min_score': STRICT_MIN_SCORE,
        'allow_single_source': STRICT_ALLOW_SINGLE_SOURCE,
        'old_top_count': len(old_top),
        'new_top_count': len(new_top),
        'moved_to_watchlist': len(moved),
    }
    engine['summary'] = f"STRICT MODE: {len(new_top)} godkendte top bets. {len(moved)} flyttet til watchlist."
    return engine


def write_md(engine):
    lines = []
    lines.append('# STRICT MODE ENGINE OUTPUT')
    lines.append('')
    lines.append(str(engine.get('summary') or ''))
    lines.append('')
    lines.append('## STRICT MODE RULES')
    lines.append('- Kun fodbold')
    lines.append('- Ingen MMA')
    lines.append('- Ingen baseball')
    lines.append('- Ingen odds over 3.00')
    lines.append('- Ingen single-source fallback picks som top bet')
    lines.append('- Ingen spreads/handicap')
    lines.append('- Max 1 bet pr kamp')
    lines.append('- Max 5 top bets')
    lines.append('- Max 1 unit')
    lines.append('')
    lines.append('## TOP BETS')
    for i, x in enumerate(engine.get('top_bets') or [], 1):
        lines.append(f"{i}. {x.get('start_local')} | {x.get('event')} | {x.get('market')} | {x.get('pick')} {x.get('point')} | odds {x.get('odds')} | units {x.get('stake_kr')} | source {x.get('source')} | score {x.get('pre_score')} | {x.get('reason')}")
    lines.append('')
    lines.append('## WATCHLIST')
    for i, x in enumerate((engine.get('watchlist') or [])[:80], 1):
        lines.append(f"{i}. {x.get('start_local')} | {x.get('event')} | {x.get('market')} | {x.get('pick')} {x.get('point')} | odds {x.get('odds')} | source {x.get('source')} | {x.get('reason')}")
    ENGINE_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    engine = load_json(ENGINE_JSON, {})
    if not isinstance(engine, dict):
        raise SystemExit('No engine JSON found')
    engine = strict_filter(engine)
    save_json(ENGINE_JSON, engine)
    write_md(engine)
    print(engine['summary'])


if __name__ == '__main__':
    main()
