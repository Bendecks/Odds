import os
import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
ENGINE_JSON = OUT / 'v6_expansion_engine.json'
PAPER_JSON = OUT / 'paper_bets.json'
SUMMARY_MD = OUT / 'paper_summary.md'

BANKROLL_KR = float(os.getenv('BANKROLL_KR', '1000'))
UNIT_PCT = float(os.getenv('UNIT_PCT', '1.0'))
MAX_EXPOSURE_PCT = float(os.getenv('MAX_EXPOSURE_PCT', '25.0'))
TRACKER_ADD_BETS = os.getenv('TRACKER_ADD_BETS', '1') == '1'
UNIT_KR = round(BANKROLL_KR * UNIT_PCT / 100.0, 2)
MAX_OPEN_EXPOSURE_KR = round(BANKROLL_KR * MAX_EXPOSURE_PCT / 100.0, 2)


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


def bet_key(b):
    return '|'.join([
        str(b.get('event','')).strip(),
        str(b.get('start') or b.get('start_local') or '').strip(),
        str(b.get('market','')).strip(),
        str(b.get('pick','')).strip(),
        str(b.get('point','')).strip(),
        str(b.get('odds','')).strip(),
    ])


def model_units(pick):
    val = pick.get('stake_units', pick.get('stake_kr', 1))
    try:
        units = float(val)
    except Exception:
        units = 1.0
    if units <= 0:
        units = 1.0
    return round(units, 2)


def normalize_pick(pick, run_id):
    units = model_units(pick)
    try:
        odds = float(str(pick.get('odds')).replace(',', '.'))
    except Exception:
        odds = None
    b = {
        'id': None,
        'status': 'open',
        'created_at': now_iso(),
        'source_run_id': run_id,
        'event': pick.get('event'),
        'sport': pick.get('sport'),
        'sport_bucket': pick.get('sport_bucket'),
        'start': pick.get('start'),
        'start_local': pick.get('start_local'),
        'market': pick.get('market'),
        'pick': pick.get('pick'),
        'point': pick.get('point'),
        'odds': odds,
        'paper_stake': round(units * UNIT_KR, 2),
        'stake_units': units,
        'unit_kr': UNIT_KR,
        'bankroll_kr': BANKROLL_KR,
        'model_stake': pick.get('stake_kr'),
        'edge_pct': pick.get('edge_pct'),
        'books': pick.get('books'),
        'pre_score': pick.get('pre_score'),
        'confidence': pick.get('confidence'),
        'reason': pick.get('reason'),
        'result': None,
        'profit': None,
        'settled_at': None,
        'notes': '',
    }
    b['key'] = bet_key(b)
    return b


def next_id(existing):
    max_n = 0
    for b in existing:
        s = str(b.get('id',''))
        if s.startswith('PB-'):
            try:
                max_n = max(max_n, int(s.split('-')[-1]))
            except Exception:
                pass
    return max_n + 1


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
    hitrate = (len(won) / (len(won)+len(lost)) * 100) if (len(won)+len(lost)) else 0
    return {
        'open_count': len(open_bets),
        'settled_count': len(settled),
        'profit': round(profit, 2),
        'roi_pct': round(roi, 2),
    }


def main():
    engine = load_json(ENGINE_JSON, {})
    top_bets = engine.get('top_bets') or []
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []

    if TRACKER_ADD_BETS:
        existing_keys = {b.get('key') for b in bets if b.get('key')}
        run_id = engine.get('generated_at') or now_iso()
        n = next_id(bets)

        for pick in top_bets:
            b = normalize_pick(pick, run_id)
            if b['key'] in existing_keys:
                continue
            b['id'] = f'PB-{n:05d}'
            n += 1
            bets.append(b)

    paper['bets'] = bets
    paper['summary'] = summarize(bets)
    save_json(PAPER_JSON, paper)

    print('Tracker run complete')


if __name__ == '__main__':
    main()
