import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path('output')
ENGINE_JSON = OUT / 'v6_expansion_engine.json'
ENGINE_MD = OUT / 'v6_expansion_engine.md'
FEEDBACK_JSON = OUT / 'v9_feedback.json'

MIN_FEEDBACK_BETS = 5
MAX_BONUS = 5.0
MAX_PENALTY = -7.0


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


def odds_bucket(odds):
    try:
        return int(float(odds or 0))
    except Exception:
        return 0


def feedback_key(item):
    return f"{item.get('market')}|odds_{odds_bucket(item.get('odds'))}"


def calc_adjustment(feedback_row):
    if not isinstance(feedback_row, dict):
        return 0.0, 'no_feedback'
    bets = int(feedback_row.get('bets') or 0)
    if bets < MIN_FEEDBACK_BETS:
        return 0.0, f'insufficient_feedback_{bets}'
    roi = float(feedback_row.get('roi_per_bet') or 0)
    hit = float(feedback_row.get('hit_rate') or 0)
    adj = 0.0
    if roi > 0:
        adj += min(roi * 2.0, MAX_BONUS)
    elif roi < 0:
        adj += max(roi * 2.0, MAX_PENALTY)
    if hit >= 58:
        adj += 2.0
    elif hit >= 53:
        adj += 1.0
    elif hit <= 40:
        adj -= 3.0
    elif hit < 45:
        adj -= 2.0
    return round(adj, 2), f"feedback bets={bets} roi_per_bet={roi} hit={hit}"


def apply_to_item(item, feedback):
    if not isinstance(item, dict):
        return item
    key = feedback_key(item)
    row = feedback.get(key)
    adj, reason = calc_adjustment(row)
    base = float(item.get('pre_score') or 0)
    item['v10_feedback_key'] = key
    item['v10_adjustment'] = adj
    item['v10_feedback_reason'] = reason
    item['v10_pre_score_before'] = round(base, 2)
    item['pre_score'] = round(base + adj, 2)
    if adj < 0:
        item['reason'] = str(item.get('reason', '')) + f' | V10 penalty {adj}: {reason}.'
    elif adj > 0:
        item['reason'] = str(item.get('reason', '')) + f' | V10 bonus +{adj}: {reason}.'
    return item


def sort_key(item):
    try:
        score = float(item.get('pre_score') or 0)
    except Exception:
        score = 0.0
    try:
        books = int(item.get('books') or 0)
    except Exception:
        books = 0
    return (score, books)


def main():
    engine = load_json(ENGINE_JSON, {})
    feedback = load_json(FEEDBACK_JSON, {})
    if not isinstance(engine, dict):
        raise SystemExit('No engine JSON found')
    if not isinstance(feedback, dict):
        feedback = {}

    applied = 0
    for section in ['top_bets', 'watchlist', 'pass']:
        rows = engine.get(section)
        if not isinstance(rows, list):
            continue
        for i, item in enumerate(rows):
            before = item.get('pre_score') if isinstance(item, dict) else None
            rows[i] = apply_to_item(item, feedback)
            if isinstance(rows[i], dict) and rows[i].get('v10_adjustment') not in (None, 0, 0.0):
                applied += 1
        if section in ['top_bets', 'watchlist']:
            rows.sort(key=sort_key, reverse=True)

    engine['mode'] = str(engine.get('mode', '')) + '+V10_ADAPTIVE_FEEDBACK'
    engine['v10'] = {
        'activated_at': now_iso(),
        'feedback_file': str(FEEDBACK_JSON),
        'feedback_patterns': len(feedback),
        'adjustments_applied': applied,
        'min_feedback_bets': MIN_FEEDBACK_BETS,
        'max_bonus': MAX_BONUS,
        'max_penalty': MAX_PENALTY,
    }
    save_json(ENGINE_JSON, engine)

    old_md = ''
    try:
        if ENGINE_MD.exists():
            old_md = ENGINE_MD.read_text(encoding='utf-8')
    except Exception:
        old_md = ''
    header = '# V10 ADAPTIVE FEEDBACK ACTIVE\n\n'
    header += f"Activated: {engine['v10']['activated_at']} | feedback patterns: {len(feedback)} | adjustments applied: {applied}\n\n"
    if feedback:
        header += '## V9 feedback used\n'
        for k, v in list(feedback.items())[:30]:
            header += f"- {k}: bets={v.get('bets')} hit={v.get('hit_rate')} roi_per_bet={v.get('roi_per_bet')}\n"
        header += '\n'
    else:
        header += 'No V9 feedback data yet. V10 is active but neutral until enough settled bets exist.\n\n'
    ENGINE_MD.write_text(header + old_md, encoding='utf-8')
    print(f'V10 applied. feedback_patterns={len(feedback)} adjustments={applied}')


if __name__ == '__main__':
    main()
