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


def now_iso(): return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        if path.exists(): return json.loads(path.read_text(encoding='utf-8'))
    except Exception: pass
    return default

def save_json(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def effective_bankroll(bets):
    profit = sum(float(b.get('profit') or 0) for b in bets if b.get('status') == 'settled')
    return round(START_BANKROLL + profit, 2)

def bet_key(b):
    return f"{b.get('event_id')}|{b.get('pick')}"

def normalize_pick(pick, bankroll):
    unit_kr = round(bankroll * UNIT_PCT / 100.0, 2)
    return {
        'id': None,
        'status': 'open',
        'created_at': now_iso(),
        'event': pick.get('event'),
        'event_id': pick.get('event_id'),
        'league': pick.get('league'),
        'start': pick.get('start'),
        'market': pick.get('market'),
        'pick': pick.get('pick'),
        'odds': pick.get('odds'),
        'paper_stake': unit_kr,
        'unit_kr': unit_kr,
        'bankroll_snapshot': bankroll,
        'result': None,
        'profit': None
    }

def next_id(existing):
    nums = [int(str(b.get('id','0')).split('-')[-1]) for b in existing if str(b.get('id','')).startswith('PB-')]
    return max(nums)+1 if nums else 1

def main():
    engine = load_json(ENGINE_JSON, {})
    top_bets = engine.get('top_bets') or []
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') or []

    bankroll = effective_bankroll(bets)
    max_exposure = bankroll * MAX_EXPOSURE_PCT / 100
    open_exposure = sum(b['paper_stake'] for b in bets if b.get('status') == 'open')

    existing = {bet_key(b) for b in bets}
    n = next_id(bets)

    if TRACKER_ADD_BETS:
        for p in top_bets:
            b = normalize_pick(p, bankroll)
            key = bet_key(b)
            if key in existing: continue
            if open_exposure + b['paper_stake'] > max_exposure: continue

            b['id'] = f"PB-{n:05d}"; n+=1
            bets.append(b)
            existing.add(key)
            open_exposure += b['paper_stake']

    paper['bets'] = bets
    paper['bankroll'] = bankroll
    save_json(PAPER_JSON, paper)

    print(f"Tracker OK | bankroll={bankroll} open_exposure={open_exposure}")

if __name__ == '__main__': main()
