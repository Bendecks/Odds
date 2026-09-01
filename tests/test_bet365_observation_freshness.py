import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from bet365_observation_freshness import apply_observation_time


def test_exact_verified_price_uses_observation_time_and_preserves_provider_update():
    rows = [{
        'bet365_verified': True,
        'event_match_method': 'exact',
        'bet365_timestamp': '2026-09-01T10:00:00+00:00',
        'bet365_odds': 2.0,
    }]
    status = {'generated_at': '2026-09-01T16:00:00+00:00', 'provider_unavailable': False}
    out, changed = apply_observation_time(rows, status)
    assert changed == 1
    assert out[0]['bet365_timestamp'] == '2026-09-01T16:00:00+00:00'
    assert out[0]['bet365_observed_at'] == '2026-09-01T16:00:00+00:00'
    assert out[0]['bet365_provider_updated_at'] == '2026-09-01T10:00:00+00:00'


def test_unverified_or_nonexact_rows_are_not_freshened():
    rows = [
        {'bet365_verified': False, 'event_match_method': 'exact', 'bet365_timestamp': 'old'},
        {'bet365_verified': True, 'event_match_method': 'diagnostic', 'bet365_timestamp': 'old'},
    ]
    out, changed = apply_observation_time(rows, {'generated_at': 'now', 'provider_unavailable': False})
    assert changed == 0
    assert [r['bet365_timestamp'] for r in out] == ['old', 'old']


def test_provider_failure_never_freshens_prices():
    rows = [{'bet365_verified': True, 'event_match_method': 'exact', 'bet365_timestamp': 'old'}]
    out, changed = apply_observation_time(rows, {'generated_at': 'now', 'provider_unavailable': True})
    assert changed == 0
    assert out[0]['bet365_timestamp'] == 'old'
