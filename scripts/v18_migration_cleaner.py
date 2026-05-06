import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
PAPER_JSON = OUT / 'paper_bets.json'
REPORT_MD = OUT / 'v18_migration_cleaner.md'

GOOD_LEAGUES = {
    'england-premier-league',
    'spain-laliga',
    'germany-bundesliga',
    'italy-serie-a',
    'france-ligue-1',
    'netherlands-eredivisie',
    'portugal-primeira-liga',
    'uefa-champions-league',
}


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


def reject_reason(b):
    sport = str(b.get('sport') or '')
    bucket = str(b.get('sport_bucket') or '')
    league = str(b.get('league') or '')
    market = str(b.get('market') or '').lower()
    odds = fnum(b.get('odds'))
    edge = fnum(b.get('edge_pct'))
    books = inum(b.get('books'))

    if not (sport.startswith('soccer_') or bucket == 'soccer'):
        return 'V18: non-football'
    if market != 'h2h':
        return 'V18: market not h2h'
    if league not in GOOD_LEAGUES:
        return 'V18: league not approved or missing'
    if odds < 1.50 or odds > 2.40:
        return 'V18: odds outside range'
    if edge < 1.5:
        return 'V18: edge below minimum'
    if books < 3:
        return 'V18: fewer than 3 prices'
    return ''


def unique_key(b):
    return f"{b.get('event_id') or b.get('event')}|{b.get('pick')}"


def summarize(bets):
    open_bets = [b for b in bets if b.get('status') == 'open']
    settled = [b for b in bets if b.get('status') == 'settled']
    won = [b for b in settled if str(b.get('result')).lower() == 'win']
    lost = [b for b in settled if str(b.get('result')).lower() == 'loss']
    push_void = [b for b in settled if str(b.get('result')).lower() in ('push', 'void')]
    open_stake = sum(fnum(b.get('paper_stake')) for b in open_bets)
    settled_stake = sum(fnum(b.get('paper_stake')) for b in settled if str(b.get('result')).lower() in ('win', 'loss'))
    profit = sum(fnum(b.get('profit')) for b in settled)
    return {
        'open_count': len(open_bets),
        'open_stake': round(open_stake, 2),
        'settled_count': len(settled),
        'won': len(won),
        'lost': len(lost),
        'push_void': len(push_void),
        'settled_stake': round(settled_stake, 2),
        'profit': round(profit, 2),
        'roi_pct': round((profit / settled_stake * 100) if settled_stake else 0, 2),
        'hitrate_pct': round((len(won) / (len(won) + len(lost)) * 100) if (len(won) + len(lost)) else 0, 2),
    }


def main():
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []

    changed = []
    seen = set()

    for b in bets:
        if b.get('status') != 'open':
            continue

        reason = reject_reason(b)
        key = unique_key(b)

        if not reason and key in seen:
            reason = 'V18: duplicate open bet'
        if not reason:
            seen.add(key)
            continue

        b['status'] = 'settled'
        b['result'] = 'void'
        b['profit'] = 0.0
        b['settled_at'] = now_iso()
        b['result_source'] = 'v18_migration_cleaner'
        b['auto_settle_note'] = reason
        b['notes'] = (str(b.get('notes') or '') + ' | Removed by V18 migration cleaner.').strip(' |')
        changed.append(b)

    paper['updated_at'] = now_iso()
    paper['bets'] = bets
    paper['summary'] = summarize(bets)
    save_json(PAPER_JSON, paper)

    lines = [
        '# V18 MIGRATION CLEANER',
        '',
        f'Generated: {now_iso()}',
        f'Voided open legacy bets: {len(changed)}',
        '',
        '## SUMMARY',
        '```json',
        json.dumps(paper['summary'], ensure_ascii=False, indent=2),
        '```',
        '',
        '## VOIDED',
    ]
    for b in changed:
        lines.append(f"- {b.get('id')} | {b.get('event')} | {b.get('pick')} @ {b.get('odds')} | {b.get('auto_settle_note')}")

    REPORT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'V18 cleaner complete. voided={len(changed)} open={paper["summary"]["open_count"]} open_stake={paper["summary"]["open_stake"]}')


if __name__ == '__main__':
    main()
