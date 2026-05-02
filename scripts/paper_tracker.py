import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
ENGINE_JSON = OUT / 'v6_expansion_engine.json'
PAPER_JSON = OUT / 'paper_bets.json'
SUMMARY_MD = OUT / 'paper_summary.md'
DEFAULT_BANKROLL = 1000


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


def bet_key(b):
    return '|'.join([
        str(b.get('event','')).strip(),
        str(b.get('start') or b.get('start_local') or '').strip(),
        str(b.get('market','')).strip(),
        str(b.get('pick','')).strip(),
        str(b.get('point','')).strip(),
        str(b.get('odds','')).strip(),
    ])


def normalize_pick(pick, run_id):
    stake = pick.get('stake_kr')
    try:
        stake = float(stake)
    except Exception:
        stake = 0.0
    if stake <= 0:
        stake = 10.0
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
        'start': pick.get('start'),
        'start_local': pick.get('start_local'),
        'market': pick.get('market'),
        'pick': pick.get('pick'),
        'point': pick.get('point'),
        'odds': odds,
        'paper_stake': stake,
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
    push = [b for b in settled if str(b.get('result')).lower() == 'push']
    open_stake = sum(float(b.get('paper_stake') or 0) for b in open_bets)
    total_staked = sum(float(b.get('paper_stake') or 0) for b in settled)
    profit = sum(float(b.get('profit') or 0) for b in settled)
    roi = (profit / total_staked * 100) if total_staked else 0
    hitrate = (len(won) / (len(won)+len(lost)) * 100) if (len(won)+len(lost)) else 0
    return {
        'open_count': len(open_bets),
        'settled_count': len(settled),
        'won': len(won),
        'lost': len(lost),
        'push': len(push),
        'open_stake': round(open_stake, 2),
        'settled_stake': round(total_staked, 2),
        'profit': round(profit, 2),
        'roi_pct': round(roi, 2),
        'hitrate_pct': round(hitrate, 2),
    }


def write_md(bets, added, skipped, engine):
    summary = summarize(bets)
    open_bets = [b for b in bets if b.get('status') == 'open']
    settled = [b for b in bets if b.get('status') == 'settled']
    with SUMMARY_MD.open('w', encoding='utf-8') as f:
        f.write('# PAPER TRACKER V1\n\n')
        f.write(f"Generated: {now_iso()}\n\n")
        f.write(f"Source mode: {engine.get('mode')}\n\n")
        f.write(f"Added this run: {added} | Skipped duplicates: {skipped}\n\n")
        f.write('## SUMMARY\n')
        f.write('```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n\n')
        f.write('## OPEN PAPER BETS\n')
        if not open_bets:
            f.write('No open paper bets.\n\n')
        for b in open_bets[-80:]:
            f.write(f"- {b.get('id')} | {b.get('start_local') or b.get('start')} | {b.get('sport')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} | {b.get('point')} | odds {b.get('odds')} | stake {b.get('paper_stake')} | edge {b.get('edge_pct')} | score {b.get('pre_score')}\n")
        f.write('\n## SETTLED PAPER BETS\n')
        if not settled:
            f.write('No settled paper bets yet.\n')
        for b in settled[-40:]:
            f.write(f"- {b.get('id')} | {b.get('result')} | profit {b.get('profit')} | {b.get('event')} | {b.get('pick')} @ {b.get('odds')}\n")


def main():
    engine = load_json(ENGINE_JSON, {})
    top_bets = engine.get('top_bets') or []
    if not isinstance(top_bets, list):
        top_bets = []
    paper = load_json(PAPER_JSON, {'created_at': now_iso(), 'bets': [], 'bankroll_start': DEFAULT_BANKROLL})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    existing_keys = {b.get('key') for b in bets if b.get('key')}
    run_id = engine.get('generated_at') or now_iso()
    n = next_id(bets)
    added = 0
    skipped = 0
    for pick in top_bets:
        if not isinstance(pick, dict):
            continue
        b = normalize_pick(pick, run_id)
        if b['key'] in existing_keys:
            skipped += 1
            continue
        b['id'] = f'PB-{n:05d}'
        n += 1
        bets.append(b)
        existing_keys.add(b['key'])
        added += 1
    paper['updated_at'] = now_iso()
    paper['bets'] = bets
    paper['summary'] = summarize(bets)
    save_json(PAPER_JSON, paper)
    write_md(bets, added, skipped, engine)
    print(f'Paper Tracker V1 complete. added={added} skipped={skipped} open={paper["summary"]["open_count"]}')


if __name__ == '__main__':
    main()
