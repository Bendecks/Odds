"""Offline probe for conservative cross-provider event matching.

Reads a captured Odds-API.io event universe plus current reference candidates and
reports exact/conservative/rejected matches. It never writes betting candidates.
Use it for tests and archived snapshots; live API collection remains separate.
"""
import json
import pathlib
import re
from collections import Counter

from event_match_diagnostics import conservative_match

CAND = pathlib.Path('data/value_candidates.json')
EVENTS = pathlib.Path('data/bet365_event_universe.json')
OUT = pathlib.Path('output/reference_resolver_probe.json')


def split_event(value):
    parts = re.split(r'\s+vs?\.?\s+', str(value or ''), maxsplit=1, flags=re.I)
    return parts if len(parts) == 2 else (None, None)


def norm(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())


def main():
    refs = json.loads(CAND.read_text()) if CAND.exists() else []
    events = json.loads(EVENTS.read_text()) if EVENTS.exists() else []
    if isinstance(events, dict):
        events = events.get('data') or events.get('events') or []
    exact = {(norm(e.get('home')), norm(e.get('away'))): e for e in events}
    rows = []
    counts = Counter()
    seen = set()
    for ref in refs:
        home, away = split_event(ref.get('event'))
        if not home:
            continue
        key = (norm(home), norm(away))
        if key in seen:
            continue
        seen.add(key)
        if key in exact:
            result = {'accepted': True, 'reason': 'exact', 'best': {'event_id': exact[key].get('id')}}
        else:
            result = conservative_match(home, away, ref.get('commence_time'), events)
        counts[result.get('reason', 'unknown')] += 1
        rows.append({'reference_event': ref.get('event'), 'reference_start': ref.get('commence_time'), **result})
    payload = {'reference_events': len(rows), 'counts': dict(counts), 'matches': rows}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'reference_events': len(rows), 'counts': dict(counts)}))


if __name__ == '__main__':
    main()
