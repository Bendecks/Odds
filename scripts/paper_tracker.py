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
        'bankroll_kr': round(BANKROLL_KR, 2),
        'unit_pct': round(UNIT_PCT, 2),
        'unit_kr': UNIT_KR,
        'max_exposure_pct': round(MAX_EXPOSURE_PCT, 2),
        'max_open_exposure_kr': MAX_OPEN_EXPOSURE_KR,
        'open_count': len(open_bets),
        'settled_count': len(settled),
        'won': len(won),
        'lost': len(lost),
        'push_void': len(push),
        'open_stake': round(open_stake, 2),
        'available_exposure_kr': round(max(0, MAX_OPEN_EXPOSURE_KR - open_stake), 2),
        'settled_stake': round(settled_stake, 2),
        'profit': round(profit, 2),
        'roi_pct': round(roi, 2),
        'hitrate_pct': round(hitrate, 2),
    }


def sorted_bets(bets):
    return sorted(bets, key=lambda b: (parse_dt(b.get('start')), str(b.get('event') or '')))


def write_md(bets, added, skipped, exposure_skipped, engine):
    summary = summarize(bets)
    open_bets = sorted_bets([b for b in bets if b.get('status') == 'open'])
    settled = sorted_bets([b for b in bets if b.get('status') == 'settled'])
    with SUMMARY_MD.open('w', encoding='utf-8') as f:
        f.write('# PAPER TRACKER V2 — BANKROLL MANAGER\n\n')
        f.write(f"Generated: {now_iso()}\n\n")
        f.write(f"Source mode: {engine.get('mode')}\n\n")
        f.write(f"Added this run: {added} | Skipped duplicates: {skipped} | Skipped exposure cap: {exposure_skipped}\n\n")
        f.write('## BANKROLL / EXPOSURE\n')
        f.write(f"Bankroll: {BANKROLL_KR:.2f} kr | Unit: {UNIT_PCT:.2f}% = {UNIT_KR:.2f} kr | Max open exposure: {MAX_EXPOSURE_PCT:.2f}% = {MAX_OPEN_EXPOSURE_KR:.2f} kr\n\n")
        f.write('## SUMMARY\n')
        f.write('```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n\n')
        f.write('## OPEN PAPER BETS — SORTED BY KICKOFF\n')
        if not open_bets:
            f.write('No open paper bets.\n\n')
        for b in open_bets[-120:]:
            f.write(f"- {b.get('id')} | {b.get('start_local') or b.get('start')} | {b.get('sport')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} {b.get('point')} | odds {b.get('odds')} | units {b.get('stake_units')} | stake {b.get('paper_stake')} kr | edge {b.get('edge_pct')} | score {b.get('pre_score')}\n")
        f.write('\n## SETTLED PAPER BETS — SORTED BY KICKOFF\n')
        if not settled:
            f.write('No settled paper bets yet.\n')
        for b in settled[-60:]:
            f.write(f"- {b.get('id')} | {b.get('start_local') or b.get('start')} | {b.get('result')} | profit {b.get('profit')} | {b.get('event')} | {b.get('pick')} @ {b.get('odds')}\n")


def main():
    engine = load_json(ENGINE_JSON, {})
    top_bets = engine.get('top_bets') or []
    if not isinstance(top_bets, list):
        top_bets = []
    top_bets = sorted(top_bets, key=lambda p: (parse_dt(p.get('start')), str(p.get('event') or '')))
    paper = load_json(PAPER_JSON, {'created_at': now_iso(), 'bets': [], 'bankroll_start': BANKROLL_KR})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    existing_keys = {b.get('key') for b in bets if b.get('key')}
    open_exposure = sum(float(b.get('paper_stake') or 0) for b in bets if b.get('status') == 'open')
    run_id = engine.get('generated_at') or now_iso()
    n = next_id(bets)
    added = 0
    skipped = 0
    exposure_skipped = 0
    for pick in top_bets:
        if not isinstance(pick, dict):
            continue
        b = normalize_pick(pick, run_id)
        if b['key'] in existing_keys:
            skipped += 1
            continue
        if open_exposure + float(b.get('paper_stake') or 0) > MAX_OPEN_EXPOSURE_KR:
            exposure_skipped += 1
            continue
        b['id'] = f'PB-{n:05d}'
        n += 1
        bets.append(b)
        existing_keys.add(b['key'])
        open_exposure += float(b.get('paper_stake') or 0)
        added += 1
    paper['updated_at'] = now_iso()
    paper['bankroll_kr'] = BANKROLL_KR
    paper['unit_pct'] = UNIT_PCT
    paper['unit_kr'] = UNIT_KR
    paper['max_exposure_pct'] = MAX_EXPOSURE_PCT
    paper['max_open_exposure_kr'] = MAX_OPEN_EXPOSURE_KR
    paper['bets'] = bets
    paper['summary'] = summarize(bets)
    save_json(PAPER_JSON, paper)
    write_md(bets, added, skipped, exposure_skipped, engine)
    print(f'Paper Tracker V2 complete. added={added} skipped={skipped} exposure_skipped={exposure_skipped} open={paper["summary"]["open_count"]} open_stake={paper["summary"]["open_stake"]}')


if __name__ == '__main__':
    main()
