import json
import pathlib

CANDIDATES = pathlib.Path('data/value_candidates.json')
STATUS = pathlib.Path('output/bet365_join_status.json')


def apply_observation_time(candidates, status):
    """Use the successful REST observation time for execution-price freshness.

    Odds-API.io market updatedAt is the bookmaker market's last-change time, not
    the time at which our REST request verified that the quoted price was still
    current. Preserve that provider timestamp separately for movement/activity
    diagnostics, while bet365_timestamp remains the exact-price observation time
    consumed by the production freshness gate.
    """
    if status.get('provider_unavailable'):
        return candidates, 0
    observed_at = status.get('generated_at')
    if not observed_at:
        return candidates, 0
    changed = 0
    for row in candidates:
        if not row.get('bet365_verified') or row.get('event_match_method') != 'exact':
            continue
        old = row.get('bet365_timestamp')
        if old and old != observed_at:
            row['bet365_provider_updated_at'] = old
        row['bet365_timestamp'] = observed_at
        row['bet365_observed_at'] = observed_at
        changed += 1
    return candidates, changed


def main():
    candidates = json.loads(CANDIDATES.read_text()) if CANDIDATES.exists() else []
    status = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    candidates, changed = apply_observation_time(candidates, status)
    CANDIDATES.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + '\n')
    print(f'Bet365 execution freshness normalized to observation time for {changed} exact verified candidates')


if __name__ == '__main__':
    main()
