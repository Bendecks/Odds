import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
PAPER_JSON = OUT / 'paper_bets.json'
PATCH_MD = OUT / 'manual_result_patch.md'

PATCHES = {
    'PB-00002': {'result': 'loss', 'note': 'Angel/Joel Alvarez def. Bryce Logan by unanimous decision; pick Bryce Logan lost.', 'source': 'manual:web:MMA Fighting'},
    'PB-00007': {'result': 'loss', 'note': 'Carlos Prates def. Jack Della Maddalena by TKO R3 3:17; pick Jack Della Maddalena lost.', 'source': 'manual:web:UFC'},
    'PB-00010': {'result': 'loss', 'note': 'Tampa Bay Rays 5 - 1 San Francisco Giants; winner=Tampa Bay Rays.', 'source': 'manual:web:Baseball-Reference'},
    'PB-00011': {'result': 'loss', 'note': 'Steve Erceg def. Tim Elliott by unanimous decision; pick Tim Elliott lost.', 'source': 'manual:web:UFC'},
    'PB-00013': {'result': 'win', 'note': 'Houston Astros 6 - 3 Boston Red Sox; winner=Houston Astros.', 'source': 'manual:web:Baseball-Reference'},
    'PB-00014': {'result': 'win', 'note': 'Cleveland Guardians 14 - 6 Athletics; winner=Cleveland Guardians.', 'source': 'manual:web:Baseball-Reference'},
    'PB-00016': {'result': 'win', 'note': 'Louie Sutherland def. Tai Tuivasa by unanimous decision; pick Louie Sutherland won.', 'source': 'manual:web:UFC/MMA Fighting'},
    'PB-00021': {'result': 'loss', 'note': 'New York Yankees 9 - 4 Baltimore Orioles; pick Baltimore Orioles lost.', 'source': 'manual:web:Baseball-Reference'},
    'PB-00023': {'result': 'win', 'note': 'Cleveland Guardians 14 - 6 Athletics; winner=Cleveland Guardians.', 'source': 'manual:web:Baseball-Reference'},
    'PB-00024': {'result': 'win', 'note': 'Sang Won Kim def. Humberto Bandenay by TKO R2 2:56.', 'source': 'manual:web:MMA Fighting/Sherdog'},
    'PB-00028': {'result': 'win', 'note': 'Los Angeles Dodgers 4 - 1 St. Louis Cardinals; winner=Los Angeles Dodgers.', 'source': 'manual:web:Reuters'},
    'PB-00029': {'result': 'loss', 'note': 'Cleveland Cavaliers 114 - 103 Toronto Raptors; pick Toronto Raptors lost.', 'source': 'manual:auto/odds-api.io'},
    'PB-00032': {'result': 'loss', 'note': 'Manchester United 3 - 2 Liverpool FC; pick Liverpool FC lost.', 'source': 'manual:web:Reuters/SBNation'},
    'PB-00033': {'result': 'win', 'note': 'Aston Villa 1 - 2 Tottenham Hotspur; pick Tottenham Hotspur won.', 'source': 'manual:web:Reuters/SkySports'},
    'PB-00036': {'result': 'loss', 'note': 'Manchester United 3 - 2 Liverpool FC; pick Liverpool FC lost.', 'source': 'manual:web:Reuters/SBNation'},
    'PB-00037': {'result': 'loss', 'note': 'Manchester United 3 - 2 Liverpool FC; pick Liverpool FC lost.', 'source': 'manual:web:Reuters/SBNation'},
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


def calc_profit(result, stake, odds):
    try:
        stake = float(stake or 0)
        odds = float(odds or 0)
    except Exception:
        return 0.0
    if result == 'win':
        return round((odds - 1.0) * stake, 2)
    if result == 'loss':
        return round(-stake, 2)
    return 0.0


def summarize(bets):
    open_bets = [b for b in bets if b.get('status') == 'open']
    settled = [b for b in bets if b.get('status') == 'settled']
    won = [b for b in settled if b.get('result') == 'win']
    lost = [b for b in settled if b.get('result') == 'loss']
    push = [b for b in settled if b.get('result') in ('push', 'void')]
    open_stake = sum(float(b.get('paper_stake') or 0) for b in open_bets)
    settled_stake = sum(float(b.get('paper_stake') or 0) for b in settled if b.get('result') in ('win', 'loss'))
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
    by_id = {str(b.get('id')): b for b in bets}
    applied = []
    skipped = []
    for bet_id, patch in PATCHES.items():
        b = by_id.get(bet_id)
        if not b:
            skipped.append((bet_id, 'missing'))
            continue
        if b.get('status') == 'settled':
            skipped.append((bet_id, 'already_settled'))
            continue
        result = patch['result']
        b['status'] = 'settled'
        b['result'] = result
        b['settled_at'] = now_iso()
        b['profit'] = calc_profit(result, b.get('paper_stake'), b.get('odds'))
        b['auto_settled'] = False
        b['auto_settle_note'] = patch['note']
        b['result_source'] = patch['source']
        b['notes'] = (str(b.get('notes') or '') + ' | Manual result patch applied.').strip(' |')
        applied.append((bet_id, result, b.get('profit'), patch['note']))
    paper['updated_at'] = now_iso()
    paper['bets'] = bets
    paper['summary'] = summarize(bets)
    save_json(PAPER_JSON, paper)
    lines = ['# MANUAL RESULT PATCH', '', f'Generated: {now_iso()}', '', f'Applied: {len(applied)}', f'Skipped: {len(skipped)}', '', '## APPLIED']
    for row in applied:
        lines.append(f'- {row[0]} | {row[1]} | profit {row[2]} | {row[3]}')
    lines.append('')
    lines.append('## SKIPPED')
    for row in skipped:
        lines.append(f'- {row[0]} | {row[1]}')
    lines.append('')
    lines.append('## SUMMARY')
    lines.append('```json')
    lines.append(json.dumps(paper['summary'], ensure_ascii=False, indent=2))
    lines.append('```')
    PATCH_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Manual result patch complete. applied={len(applied)} skipped={len(skipped)}')


if __name__ == '__main__':
    main()
