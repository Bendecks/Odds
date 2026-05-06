import os
import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
ENGINE_JSON = OUT / 'v6_expansion_engine.json'
PAPER_JSON = OUT / 'paper_bets.json'
SUMMARY_MD = OUT / 'paper_summary.md'

START_BANKROLL = float(os.getenv('BANKROLL_KR', '1000'))
UNIT_PCT = float(os.getenv('UNIT_PCT', '1.0'))
MAX_EXPOSURE_PCT = float(os.getenv('MAX_EXPOSURE_PCT', '25.0'))
TRACKER_ADD_BETS = os.getenv('TRACKER_ADD_BETS', '1') == '1'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_dt(v):
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except Exception:
        return datetime.max.replace(tzinfo=timezone.utc)


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


def effective_bankroll(bets):
    profit = sum(fnum(b.get('profit')) for b in bets if b.get('status') == 'settled')
    return round(START_BANKROLL + profit, 2)


def bet_key(b):
    return f"{b.get('event_id') or b.get('event')}|{b.get('market')}|{b.get('pick')}"


def next_id(existing):
    nums = []
    for b in existing:
        s = str(b.get('id', ''))
        if s.startswith('PB-'):
            try:
                nums.append(int(s.split('-')[-1]))
            except Exception:
                pass
    return max(nums) + 1 if nums else 1


def normalize_pick(pick, bankroll):
    stake = fnum(pick.get('stake_kr'))
    if stake <= 0:
        stake = round(bankroll * UNIT_PCT / 100.0, 2)
    stake = round(stake, 2)
    return {
        'id': None,
        'status': 'open',
        'created_at': now_iso(),
        'event': pick.get('event'),
        'event_id': pick.get('event_id'),
        'sport': pick.get('sport'),
        'sport_bucket': pick.get('sport_bucket'),
        'league': pick.get('league'),
        'source_league_slug': pick.get('source_league_slug'),
        'start': pick.get('start'),
        'start_local': pick.get('start_local'),
        'market': pick.get('market'),
        'pick': pick.get('pick'),
        'point': pick.get('point'),
        'odds': pick.get('odds'),
        'median_odds': pick.get('median_odds'),
        'edge_pct': pick.get('edge_pct'),
        'books': pick.get('books'),
        'pre_score': pick.get('pre_score'),
        'confidence': pick.get('confidence'),
        'reason': pick.get('reason'),
        'paper_stake': stake,
        'stake_units': round(stake / max(bankroll * UNIT_PCT / 100.0, 0.01), 2),
        'unit_kr': round(bankroll * UNIT_PCT / 100.0, 2),
        'bankroll_snapshot': bankroll,
        'result': None,
        'profit': None,
        'key': None,
    }


def summarize(bets):
    bankroll = effective_bankroll(bets)
    max_open = round(bankroll * MAX_EXPOSURE_PCT / 100.0, 2)
    open_bets = [b for b in bets if b.get('status') == 'open']
    settled = [b for b in bets if b.get('status') == 'settled']
    won = [b for b in settled if str(b.get('result')).lower() == 'win']
    lost = [b for b in settled if str(b.get('result')).lower() == 'loss']
    push_void = [b for b in settled if str(b.get('result')).lower() in ('push', 'void')]
    open_stake = sum(fnum(b.get('paper_stake')) for b in open_bets)
    settled_stake = sum(fnum(b.get('paper_stake')) for b in settled if str(b.get('result')).lower() in ('win', 'loss'))
    profit = sum(fnum(b.get('profit')) for b in settled)
    return {
        'bankroll_kr': bankroll,
        'unit_pct': UNIT_PCT,
        'unit_kr': round(bankroll * UNIT_PCT / 100.0, 2),
        'max_exposure_pct': MAX_EXPOSURE_PCT,
        'max_open_exposure_kr': max_open,
        'open_count': len(open_bets),
        'open_stake': round(open_stake, 2),
        'available_exposure_kr': round(max(0, max_open - open_stake), 2),
        'settled_count': len(settled),
        'won': len(won),
        'lost': len(lost),
        'push_void': len(push_void),
        'settled_stake': round(settled_stake, 2),
        'profit': round(profit, 2),
        'roi_pct': round((profit / settled_stake * 100) if settled_stake else 0, 2),
        'hitrate_pct': round((len(won) / (len(won) + len(lost)) * 100) if (len(won) + len(lost)) else 0, 2),
    }


def write_summary_md(paper):
    bets = paper.get('bets') or []
    summary = paper.get('summary') or summarize(bets)
    open_bets = sorted([b for b in bets if b.get('status') == 'open'], key=lambda b: parse_dt(b.get('start')))
    lines = ['# PAPER SUMMARY', '', '```json', json.dumps(summary, ensure_ascii=False, indent=2), '```', '', '## OPEN BETS']
    for b in open_bets:
        lines.append(f"- {b.get('id')} | {b.get('start_local') or b.get('start')} | {b.get('league')} | {b.get('event')} | {b.get('pick')} @ {b.get('odds')} | edge {b.get('edge_pct')} | stake {b.get('paper_stake')} kr")
    SUMMARY_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    engine = load_json(ENGINE_JSON, {})
    top_bets = engine.get('top_bets') if isinstance(engine.get('top_bets'), list) else []
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []

    bankroll = effective_bankroll(bets)
    max_exposure = bankroll * MAX_EXPOSURE_PCT / 100.0
    open_exposure = sum(fnum(b.get('paper_stake')) for b in bets if b.get('status') == 'open')
    existing = {bet_key(b) for b in bets if b.get('status') == 'open'}
    n = next_id(bets)
    added = 0
    skipped_duplicate = 0
    skipped_exposure = 0

    if TRACKER_ADD_BETS:
        for p in top_bets:
            if not isinstance(p, dict):
                continue
            b = normalize_pick(p, bankroll)
            key = bet_key(b)
            b['key'] = key
            if key in existing:
                skipped_duplicate += 1
                continue
            if open_exposure + fnum(b.get('paper_stake')) > max_exposure:
                skipped_exposure += 1
                continue
            b['id'] = f'PB-{n:05d}'
            n += 1
            bets.append(b)
            existing.add(key)
            open_exposure += fnum(b.get('paper_stake'))
            added += 1

    paper['updated_at'] = now_iso()
    paper['bets'] = bets
    paper['bankroll'] = effective_bankroll(bets)
    paper['summary'] = summarize(bets)
    paper['last_tracker_run'] = {
        'generated_at': now_iso(),
        'engine_mode': engine.get('mode'),
        'engine_summary': engine.get('summary'),
        'add_bets': TRACKER_ADD_BETS,
        'added': added,
        'skipped_duplicate': skipped_duplicate,
        'skipped_exposure': skipped_exposure,
    }
    save_json(PAPER_JSON, paper)
    write_summary_md(paper)
    print(f"Tracker OK | added={added} dup={skipped_duplicate} exposure_skip={skipped_exposure} bankroll={paper['bankroll']} open_exposure={paper['summary']['open_stake']}")


if __name__ == '__main__':
    main()
