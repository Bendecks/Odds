import json
import os
import pathlib
from datetime import datetime, timezone

import requests

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)

STATUS_JSON = OUT / 'api_quota_status.json'
STATUS_MD = OUT / 'api_quota_status.md'

THE_ODDS_API_KEY = os.getenv('THE_ODDS_API_KEY', '')
ODDS_API_IO_KEY = os.getenv('ODDS_API_IO_KEY', '')


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def safe_headers(headers):
    wanted = [
        'x-requests-remaining',
        'x-requests-used',
        'x-requests-last',
        'x-ratelimit-limit',
        'x-ratelimit-remaining',
        'x-ratelimit-reset',
        'ratelimit-limit',
        'ratelimit-remaining',
        'ratelimit-reset',
        'retry-after',
    ]
    lower_map = {str(k).lower(): str(v) for k, v in dict(headers).items()}
    return {k: lower_map.get(k) for k in wanted if lower_map.get(k) is not None}


def request_status(name, url, params):
    if not params.get('apiKey'):
        return {
            'api': name,
            'configured': False,
            'ok': False,
            'status_code': None,
            'headers': {},
            'error': 'Missing API key secret',
            'sample_items': None,
        }

    try:
        response = requests.get(url, params=params, timeout=30)
        body = None
        sample_items = None
        try:
            body = response.json()
            if isinstance(body, list):
                sample_items = len(body)
            elif isinstance(body, dict):
                sample_items = list(body.keys())[:10]
        except Exception:
            body = response.text[:300]

        return {
            'api': name,
            'configured': True,
            'ok': response.ok,
            'status_code': response.status_code,
            'headers': safe_headers(response.headers),
            'error': None if response.ok else str(body)[:500],
            'sample_items': sample_items,
        }
    except Exception as exc:
        return {
            'api': name,
            'configured': True,
            'ok': False,
            'status_code': None,
            'headers': {},
            'error': str(exc)[:500],
            'sample_items': None,
        }


def explain(entry):
    h = entry.get('headers') or {}
    if not entry.get('configured'):
        return 'API-nøgle mangler i GitHub Secrets.'
    if not entry.get('ok'):
        if entry.get('status_code') == 429:
            return 'Rate limit er ramt. Se retry-after eller reset-header, hvis den findes.'
        return 'Kaldet fejlede. Se error-feltet.'

    remaining = h.get('x-requests-remaining') or h.get('x-ratelimit-remaining') or h.get('ratelimit-remaining')
    limit = h.get('x-ratelimit-limit') or h.get('ratelimit-limit')
    reset = h.get('x-ratelimit-reset') or h.get('ratelimit-reset')
    used = h.get('x-requests-used')

    bits = []
    if remaining is not None:
        bits.append(f'{remaining} requests tilbage')
    if limit is not None:
        bits.append(f'limit {limit}')
    if used is not None:
        bits.append(f'{used} brugt')
    if reset is not None:
        bits.append(f'reset {reset}')
    return ', '.join(bits) if bits else 'Kald OK, men API’et returnerede ikke tydelige quota-headers.'


def build_report(status):
    lines = [
        '# API QUOTA STATUS',
        '',
        f'Generated: {status["generated_at"]}',
        '',
        'Dette workflow laver kun små status-kald. Det henter ikke odds for kampe.',
        '',
    ]
    for entry in status['apis']:
        lines.extend([
            f'## {entry["api"]}',
            '',
            f'Configured: {entry.get("configured")}',
            f'OK: {entry.get("ok")}',
            f'Status code: {entry.get("status_code")}',
            f'Verdict: {explain(entry)}',
            '',
            'Headers:',
            '```json',
            json.dumps(entry.get('headers') or {}, ensure_ascii=False, indent=2),
            '```',
            '',
        ])
        if entry.get('error'):
            lines.extend(['Error:', '```text', str(entry.get('error')), '```', ''])
    return '\n'.join(lines) + '\n'


def main():
    status = {
        'generated_at': now_iso(),
        'note': 'Small API quota check only. Does not fetch odds markets.',
        'apis': [],
    }

    # The Odds API: /v4/sports is the smallest practical authenticated check and returns quota headers.
    status['apis'].append(request_status(
        'the-odds-api',
        'https://api.the-odds-api.com/v4/sports',
        {'apiKey': THE_ODDS_API_KEY},
    ))

    # odds-api.io: /leagues is used as a light authenticated check. Avoid /odds endpoints here.
    status['apis'].append(request_status(
        'odds-api.io',
        'https://api.odds-api.io/v3/leagues',
        {'apiKey': ODDS_API_IO_KEY, 'sport': 'football'},
    ))

    STATUS_JSON.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    STATUS_MD.write_text(build_report(status), encoding='utf-8')

    for entry in status['apis']:
        print(f"{entry['api']}: ok={entry.get('ok')} status={entry.get('status_code')} {explain(entry)}")


if __name__ == '__main__':
    main()
