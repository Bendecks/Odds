import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
PAPER_JSON = OUT / 'paper_bets.json'
RESULTS_JSON = OUT / 'paper_results.json'
SUMMARY_MD = OUT / 'paper_settler_summary.md'

VALID_RESULTS = {'win', 'loss', 'push', 'void'}


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


def calc_profit(result, stake, odds):
    try:
        stake = float(stake or 0)
        odds = float(odds or 0)
    except Exception:
        return 0.0
    result = str(result or '').lower().strip()
    if result == 'win':
        return round((odds - 1.0) * stake, 2)
    if result == 'loss':
        return round(-stake, 2)
    if result in ('push', 'void'):
        return 0.0
    return 0.0


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


def normalize_results(raw):
    if isinstance(raw, dict) and isinstance(raw.get('results'), list):
        raw = raw.get('results')
    if not isinstance(raw, list):
        return []
    out = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        bet_id = str(r.get('id') or r.get('bet_id') or '').strip()
        result = str(r.get('result') or '').lower().strip()
        if not bet_id or result not in VALID_RESULTS:
            continue
        out.append({
            'id': bet_id,
            'result': result,
            'notes': r.get('notes',''),
            'settled_at': r.get('settled_at') or now_iso(),
        })
    return out


def write_md(bets, applied, skipped, missing):
    summary = summarize(bets)
    open_bets = [b for b in bets if b.get('status') == 'open']
    settled = [b for b in bets if b.get('status') == 'settled']
    with SUMMARY_MD.open('w', encoding='utf-8') as f:
        f.write('# PAPER SETTLER V1\n\n')
        f.write(f'Generated: {now_iso()}\n\n')
        f.write(f'Applied: {applied} | Skipped: {skipped} | Missing IDs: {missing}\n\n')
        f.write('## SUMMARY\n')
        f.write('```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n\n')
        f.write('## RECENT SETTLED\n')
        if not settled:
            f.write('No settled paper bets yet.\n\n')
        for b in settled[-60:]:
            f.write(f"- {b.get('id')} | {b.get('result')} | profit {b.get('profit')} | stake {b.get('paper_stake')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} | odds {b.get('odds')}\n")
        f.write('\n## OPEN BETS\n')
        if not open_bets:
            f.write('No open paper bets.\n')
        for b in open_bets[-80:]:
            f.write(f"- {b.get('id')} | {b.get('start_local') or b.get('start')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} | odds {b.get('odds')} | stake {b.get('paper_stake')}\n")


def main():
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    results = normalize_results(load_json(RESULTS_JSON, {'results': []}))
    by_id = {str(b.get('id')): b for b in bets if b.get('id')}
    applied = 0
    skipped = 0
    missing = 0
    for r in results:
        b = by_id.get(r['id'])
        if not b:
            missing += 1
            continue
        if b.get('status') == 'settled':
            skipped += 1
            continue
        b['status'] = 'settled'
        b['result'] = r['result']
        b['settled_at'] = r['settled_at']
        b['profit'] = calc_profit(r['result'], b.get('paper_stake'), b.get('odds'))
        if r.get('notes'):
            b['notes'] = r.get('notes')
        applied += 1
    paper['updated_at'] = now_iso()
    paper['bets'] = bets
    paper['summary'] = summarize(bets)
    save_json(PAPER_JSON, paper)
    write_md(bets, applied, skipped, missing)
    print(f'Paper Settler V1 complete. applied={applied} skipped={skipped} missing={missing}')


if __name__ == '__main__':
    main()
