import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
PAPER_JSON = OUT / 'paper_bets.json'
MIGRATION_MD = OUT / 'strict_mode_migration.md'

STRICT_ALLOWED_SPORT_PREFIXES = (
    'soccer_epl',
    'soccer_spain_la_liga',
    'soccer_germany_bundesliga',
    'soccer_football_data',
    'soccer_odds_api_io',
)
STRICT_ALLOWED_MARKETS = ('h2h',)
STRICT_MIN_ODDS = 1.50
STRICT_MAX_ODDS = 2.50
STRICT_MIN_SCORE = 7.0


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


def violates_v21(bet):
    sport = str(bet.get('sport') or '')
    market = str(bet.get('market') or '').lower()
    try:
        odds = float(bet.get('odds') or 0)
    except Exception:
        odds = 0.0
    try:
        score = float(bet.get('pre_score') or 0)
    except Exception:
        score = 0.0

    if not sport.startswith(STRICT_ALLOWED_SPORT_PREFIXES):
        return 'legacy_void: sport outside Strict V2.1'
    if market not in STRICT_ALLOWED_MARKETS:
        return 'legacy_void: market outside Strict V2.1'
    if odds < STRICT_MIN_ODDS or odds > STRICT_MAX_ODDS:
        return 'legacy_void: odds outside Strict V2.1'
    if score < STRICT_MIN_SCORE:
        return 'legacy_void: score below Strict V2.1'
    return ''


def summarize(bets):
    open_bets = [b for b in bets if b.get('status') == 'open']
    settled = [b for b in bets if b.get('status') == 'settled']
    won = [b for b in settled if str(b.get('result')).lower() == 'win']
    lost = [b for b in settled if str(b.get('result')).lower() == 'loss']
    push = [b for b in settled if str(b.get('result')).lower() in ('push', 'void')]
    open_stake = sum(float(b.get('paper_stake') or 0) for b in open_bets)
    settled_stake = sum(float(b.get('paper_stake') or 0) for b in settled if str(b.get('result')).lower() in ('win','loss'))
    profit = sum(float(b.get('profit') or 0) for b in settled)
    roi = (profit / settled_stake * 100) if settled_stake else 0
    hitrate = (len(won) / (len(won) + len(lost)) * 100) if (len(won) + len(lost)) else 0
    return {
        'open_count': len(open_bets),
        'settled_count': len(settled),
        'won': len(won),
        'lost': len(lost),
        'push_void': len(push),
        'open_stake': round(open_stake, 2),
        'settled_stake': round(settled_stake, 2),
        'profit': round(profit, 2),
        'roi_pct': round(roi, 2),
        'hitrate_pct': round(hitrate, 2),
    }


def main():
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    migrated = []

    for b in bets:
        if b.get('status') != 'open':
            continue
        reason = violates_v21(b)
        if not reason:
            continue
        b['status'] = 'settled'
        b['result'] = 'void'
        b['profit'] = 0.0
        b['settled_at'] = now_iso()
        b['result_source'] = 'strict_mode_v2_1_migration'
        b['auto_settle_note'] = reason
        b['notes'] = (str(b.get('notes') or '') + ' | Removed from active test by Strict Mode V2.1 migration.').strip(' |')
        migrated.append(b)

    paper['updated_at'] = now_iso()
    paper['bets'] = bets
    paper['summary'] = summarize(bets)
    save_json(PAPER_JSON, paper)

    lines = [
        '# STRICT MODE V2.1 MIGRATION',
        '',
        f'Generated: {now_iso()}',
        '',
        f'Migrated open legacy bets to void: {len(migrated)}',
        '',
        '## MIGRATED',
    ]
    for b in migrated:
        lines.append(f"- {b.get('id')} | {b.get('start_local')} | {b.get('sport')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} @ {b.get('odds')} | {b.get('auto_settle_note')}")
    lines.append('')
    lines.append('## SUMMARY')
    lines.append('```json')
    lines.append(json.dumps(paper['summary'], ensure_ascii=False, indent=2))
    lines.append('```')
    MIGRATION_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Strict migration complete. migrated={len(migrated)} open={paper["summary"]["open_count"]}')


if __name__ == '__main__':
    main()
