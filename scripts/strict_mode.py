import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
ENGINE_JSON = OUT / 'v6_expansion_engine.json'
ENGINE_MD = OUT / 'v6_expansion_engine.md'

ALLOWED_LEAGUES = {
    'england-premier-league',
    'spain-laliga',
    'germany-bundesliga',
    'italy-serie-a',
    'france-ligue-1',
    'netherlands-eredivisie',
    'portugal-primeira-liga',
    'uefa-champions-league',
}
ALLOWED_MARKETS = {'h2h'}
MIN_ODDS = 1.50
MAX_ODDS = 2.40
MIN_EDGE = 1.5
MIN_BOOKS = 3
MAX_TOP_BETS = 8


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


def fnum(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def inum(v):
    try:
        return int(v)
    except Exception:
        return 0


def rejection_reason(item, seen_events):
    league = str(item.get('league') or '')
    market = str(item.get('market') or '').lower()
    odds = fnum(item.get('odds'))
    edge = fnum(item.get('edge_pct'))
    books = inum(item.get('books'))
    event_id = str(item.get('event_id') or item.get('event') or '')

    if league not in ALLOWED_LEAGUES:
        return 'Liga er ikke V18-godkendt.'
    if market not in ALLOWED_MARKETS:
        return 'Kun kampvinder.'
    if not (MIN_ODDS <= odds <= MAX_ODDS):
        return f'Odds udenfor {MIN_ODDS}-{MAX_ODDS}.'
    if edge < MIN_EDGE:
        return f'Edge under {MIN_EDGE}%.'
    if books < MIN_BOOKS:
        return f'For få bookmaker-priser ({books}).'
    if event_id in seen_events:
        return 'Kun 1 bet pr kamp.'
    return ''


def normalize_watch(item, reason):
    item = dict(item)
    item['role'] = 'WATCHLIST'
    item['stake_kr'] = 0
    item['reason'] = reason
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
        reason = rejection_reason(item, seen_events)
        if reason:
            moved.append(normalize_watch(item, reason))
            continue
        clean = dict(item)
        clean['role'] = 'PRIMARY_V18_STRICT'
        clean['reason'] = clean.get('reason') or 'Godkendt af V18 strict filter.'
        new_top.append(clean)
        seen_events.add(str(item.get('event_id') or item.get('event') or ''))
        if len(new_top) >= MAX_TOP_BETS:
            break

    engine['top_bets'] = new_top
    engine['watchlist'] = moved + old_watch
    original_mode = engine.get('mode') or 'UNKNOWN_ENGINE'
    engine['mode'] = f'{original_mode}+STRICT_V18'
    engine['summary'] = f"V18 strict: {len(new_top)} bets"
    engine['strict_v18'] = {
        'applied_at': now_iso(),
        'moved_to_watchlist': len(moved),
        'top_count_after_strict': len(new_top),
    }
    return engine


def write_md(engine):
    lines = [
        f"# {engine.get('mode')}",
        '',
        engine.get('summary', ''),
        '',
        '## DIAGNOSTICS',
        '```json',
        json.dumps(engine.get('diagnostics') or {}, ensure_ascii=False, indent=2),
        '```',
        '',
        '## TOP BETS',
    ]
    if not engine.get('top_bets'):
        lines.append('Ingen valide bets fundet i dette run.')
    for i, x in enumerate(engine.get('top_bets') or [], 1):
        lines.append(f"{i}. {x.get('start_local') or x.get('start')} | {x.get('league')} | {x.get('event')} | {x.get('pick')} @ {x.get('odds')} | edge {x.get('edge_pct')} | books {x.get('books')}")
    ENGINE_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    engine = load_json(ENGINE_JSON, {})
    engine = strict_filter(engine)
    save_json(ENGINE_JSON, engine)
    write_md(engine)
    print(engine['summary'])


if __name__ == '__main__':
    main()
