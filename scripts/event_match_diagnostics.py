"""Conservative diagnostics for cross-provider football event matching.

This module does not alter candidates or betting decisions. It provides reusable
name/time similarity helpers so ambiguous provider joins can be measured before
any resolver is allowed into the decision path.
"""
from difflib import SequenceMatcher
from datetime import datetime, timezone
import re
import unicodedata

NOISE = {'fc', 'cf', 'sc', 'afc', 'ac', 'club', 'football', 'futbol', 'de', 'the'}


def team_norm(value):
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    words = re.findall(r'[a-z0-9]+', text)
    useful = [word for word in words if word not in NOISE]
    return ''.join(useful) or ''.join(words)


def team_similarity(left, right):
    left, right = team_norm(left), team_norm(right)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()


def parse_start(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)
    except Exception:
        return None


def score_candidate(ref_home, ref_away, ref_start, event):
    candidate_start = parse_start(event.get('date') or event.get('startTime') or event.get('commence_time'))
    ref_start = parse_start(ref_start)
    if not ref_start or not candidate_start:
        return None
    home_score = team_similarity(ref_home, event.get('home'))
    away_score = team_similarity(ref_away, event.get('away'))
    return {
        'event_id': event.get('id'),
        'home': event.get('home'),
        'away': event.get('away'),
        'time_delta_minutes': round(abs((candidate_start-ref_start).total_seconds())/60, 2),
        'home_score': round(home_score, 4),
        'away_score': round(away_score, 4),
        'combined_score': round((home_score+away_score)/2, 4),
    }


def conservative_match(ref_home, ref_away, ref_start, events, max_minutes=20, min_team=0.72, min_score=0.84, min_margin=0.08):
    scored=[]
    for event in events:
        row=score_candidate(ref_home, ref_away, ref_start, event)
        if not row or row['time_delta_minutes'] > max_minutes:
            continue
        if min(row['home_score'], row['away_score']) < min_team:
            continue
        scored.append(row)
    scored.sort(key=lambda row: (-row['combined_score'], row['time_delta_minutes']))
    if not scored:
        return {'accepted': False, 'reason': 'no_candidate'}
    best=scored[0]
    second=scored[1]['combined_score'] if len(scored)>1 else 0.0
    margin=round(best['combined_score']-second, 4)
    if best['combined_score'] < min_score:
        return {'accepted': False, 'reason': 'score_below_threshold', 'best': best, 'margin': margin}
    if len(scored)>1 and margin < min_margin:
        return {'accepted': False, 'reason': 'ambiguous', 'best': best, 'margin': margin}
    return {'accepted': True, 'reason': 'time_team_match', 'best': best, 'margin': margin}
