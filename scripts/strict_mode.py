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
    'soccer_odds_api_io'
)

STRICT_ALLOWED_MARKETS = ('h2h',)
STRICT_MAX_ODDS = 3.00
STRICT_MAX_TOP_BETS = 5
STRICT_MIN_SCORE = 7.0
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


def is_allowed(item):
    sport = str(item.get('sport') or '')
    return sport.startswith(STRICT_ALLOWED_SPORT_PREFIXES)


def rejection_reason(item, seen_events):
    market = str(item.get('market') or '').lower()
    odds = float(item.get('odds') or 0)
    score = float(item.get('pre_score') or 0)
    event = str(item.get('event') or '')

    if not is_allowed(item):
        return 'Kun top fodboldligaer.'

    if market not in STRICT_ALLOWED_MARKETS:
        return 'Kun kampvinder (ingen over/under).'

    if odds <= 0 or odds > STRICT_MAX_ODDS:
        return f'Odds over {STRICT_MAX_ODDS}.'

    if item.get('single_source') and not STRICT_ALLOW_SINGLE_SOURCE:
        return 'Single-source ikke tilladt.'

    if score < STRICT_MIN_SCORE:
        return f'Score < {STRICT_MIN_SCORE}.'

    if event in seen_events:
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
        clean['role'] = 'PRIMARY_STRICT_V2'
        clean['stake_kr'] = 1
        clean['strict_mode'] = True
        clean['reason'] = 'Godkendt (Strict V2)'

        new_top.append(clean)
        seen_events.add(str(item.get('event')))

        if len(new_top) >= STRICT_MAX_TOP_BETS:
            break

    for item in old_top:
        if isinstance(item, dict) and item not in new_top and item not in moved:
            moved.append(normalize_watch(item, 'Ikke blandt top 5'))

    engine['top_bets'] = new_top
    engine['watchlist'] = moved + old_watch
    engine['mode'] = 'STRICT_MODE_V2'

    engine['summary'] = f"STRICT V2: {len(new_top)} bets"

    return engine


def write_md(engine):
    lines = []
    lines.append('# STRICT MODE V2')
    lines.append(engine.get('summary', ''))
    lines.append('')

    for i, x in enumerate(engine.get('top_bets') or [], 1):
        lines.append(f"{i}. {x.get('event')} | {x.get('pick')} @ {x.get('odds')}")

    ENGINE_MD.write_text('\n'.join(lines), encoding='utf-8')


def main():
    engine = load_json(ENGINE_JSON, {})
    engine = strict_filter(engine)
    save_json(ENGINE_JSON, engine)
    write_md(engine)
    print(engine['summary'])


if __name__ == '__main__':
    main()
