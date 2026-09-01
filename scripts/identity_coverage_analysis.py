import json, pathlib
from collections import Counter

CAND = pathlib.Path('data/value_candidates.json')
OUT = pathlib.Path('output/identity_coverage_analysis.json')


def exact_identity(row):
    return bool(row.get('bet365_verified') and row.get('bet365_event_id') and row.get('event_match_method') == 'exact')


def build(rows):
    candidate = Counter(str(r.get('market') or 'unknown') for r in rows)
    exact = Counter(str(r.get('market') or 'unknown') for r in rows if exact_identity(r))
    reference_ready = Counter(
        str(r.get('market') or 'unknown') for r in rows
        if exact_identity(r) and int(r.get('books') or 0) >= 3
    )
    markets = []
    for market, total in candidate.items():
        ex = exact.get(market, 0)
        ready = reference_ready.get(market, 0)
        missing = total - ex
        markets.append({
            'market': market,
            'candidate_rows': total,
            'exact_rows': ex,
            'missing_exact_rows': missing,
            'exact_rate': round(ex / total, 4) if total else 0,
            'reference_ready_rows': ready,
            'reference_ready_rate': round(ready / total, 4) if total else 0,
        })
    markets.sort(key=lambda x: (-x['missing_exact_rows'], x['market']))
    return {
        'candidate_rows': len(rows),
        'exact_rows': sum(exact.values()),
        'missing_exact_rows': len(rows) - sum(exact.values()),
        'markets': markets,
        'priority_note': 'Diagnostic only. High missing-exact counts identify where exact provider identity/market availability can add the most evaluated PAPER candidates; they do not authorize fuzzy joins.',
    }


def main():
    try:
        rows = json.loads(CAND.read_text())
    except Exception:
        rows = []
    report = build(rows)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
