import json
import os
import pathlib
import re
from datetime import datetime, timezone

ROOT = pathlib.Path('.')
INBOX = ROOT / 'inbox' / 'possible_bets'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

ANALYSIS_JSON = OUT / 'ocr_possible_bets_analysis.json'
ANALYSIS_MD = OUT / 'ocr_possible_bets_analysis.md'

MAX_FILES = int(os.getenv('OCR_MAX_FILES', '25'))

TEAM_ALIASES = {
    'CLE Cavaliers': 'Cleveland Cavaliers',
    'DET Pistons': 'Detroit Pistons',
    'LA Lakers': 'Los Angeles Lakers',
    'OKC Thunder': 'Oklahoma City Thunder',
}

SPORT_WORDS = {
    'basketball': 'basketball',
    'NBA': 'basketball_nba',
    'Euroleague': 'basketball_euroleague',
    'fodbold': 'football',
    'football': 'football',
    'tennis': 'tennis',
    'ishockey': 'icehockey',
    'hockey': 'icehockey',
}

NOISE_PATTERNS = [
    r'^bet$', r'^365$', r'^bet365$', r'^bet365\.dk$', r'^Session ', r'^Ansvarsfuldt spil$',
    r'^ÅBN$', r'^Åbn i appen', r'^Sport$', r'^Live$', r'^Casino$', r'^Væddemål$',
    r'^AKKUMULATOR', r'^Matchkupon$', r'^Ekstra$', r'^Alle$', r'^Alle kampe$', r'^Næste ',
    r'^Hjem$', r'^<$', r'^=$', r'^•', r'^\.\.$',
]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def read_text_file(path):
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding='latin-1', errors='ignore')


def list_input_files():
    if not INBOX.exists():
        return []
    files = []
    for p in INBOX.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.txt', '.json', '.md'}:
            files.append(p)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:MAX_FILES]


def extract_text(path):
    raw = read_text_file(path)
    if path.suffix.lower() == '.json':
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return str(data.get('ocr_text') or data.get('text') or data.get('content') or raw)
        except Exception:
            pass
    return raw


def clean_lines(text):
    lines = []
    for line in str(text).splitlines():
        x = line.strip()
        if not x:
            continue
        if any(re.search(p, x, flags=re.I) for p in NOISE_PATTERNS):
            continue
        lines.append(x)
    return lines


def is_odds(x):
    try:
        v = float(str(x).replace(',', '.'))
        return 1.01 <= v <= 100.0
    except Exception:
        return False


def parse_odds(x):
    try:
        return float(str(x).replace(',', '.'))
    except Exception:
        return None


def is_handicap(x):
    return bool(re.fullmatch(r'[+-]\d+(?:[\.,]\d+)?', str(x)))


def is_total_line(x):
    return bool(re.fullmatch(r'[OU]\s*\d+(?:[\.,]\d+)?', str(x), flags=re.I))


def looks_like_time(x):
    return bool(re.fullmatch(r'\d{1,2}:\d{2}', str(x)))


def looks_like_team(x):
    if is_odds(x) or is_handicap(x) or is_total_line(x) or looks_like_time(x):
        return False
    if len(x) < 3:
        return False
    if re.search(r'[A-Za-zÆØÅæøå]', x) and not re.search(r'^(Handicap|Total|Point|Rebounds|Assist|Lige På|Point O/U)$', x, flags=re.I):
        return True
    return False


def normalize_team(x):
    return TEAM_ALIASES.get(x, x)


def infer_sport(lines):
    sport = 'unknown'
    for line in lines:
        if line in SPORT_WORDS:
            sport = SPORT_WORDS[line]
    return sport


def parse_basketball_like(lines):
    events = []
    i = 0
    while i < len(lines) - 1:
        home = lines[i]
        away = lines[i + 1]
        if not looks_like_team(home) or not looks_like_team(away):
            i += 1
            continue

        if home.lower() in {'handicap', 'total', 'point', 'rebound', 'assist'} or away.lower() in {'handicap', 'total', 'point', 'rebound', 'assist'}:
            i += 1
            continue

        chunk = lines[i + 2:i + 14]
        odds_numbers = [parse_odds(x) for x in chunk if is_odds(x)]
        handicaps = [x for x in chunk if is_handicap(x)]
        totals = [x for x in chunk if is_total_line(x)]
        times = [x for x in chunk if looks_like_time(x)]

        if len(odds_numbers) >= 2 and (handicaps or totals or times):
            event = {
                'home': normalize_team(home),
                'away': normalize_team(away),
                'raw_home': home,
                'raw_away': away,
                'start_time_visible': times[0] if times else None,
                'markets': [],
                'raw_chunk': chunk,
            }

            if handicaps and len(odds_numbers) >= 2:
                event['markets'].append({
                    'market': 'handicap',
                    'selection': event['home'],
                    'line': handicaps[0],
                    'odds': odds_numbers[0],
                    'confidence': 'medium',
                    'explanation': f'{event["home"]} får handicap {handicaps[0]} til odds {odds_numbers[0]}',
                })
                if len(handicaps) > 1 and len(odds_numbers) >= 5:
                    event['markets'].append({
                        'market': 'handicap',
                        'selection': event['away'],
                        'line': handicaps[1],
                        'odds': odds_numbers[4],
                        'confidence': 'medium',
                        'explanation': f'{event["away"]} får handicap {handicaps[1]} til odds {odds_numbers[4]}',
                    })

            if totals and len(odds_numbers) >= 4:
                event['markets'].append({
                    'market': 'total',
                    'selection': 'Over' if totals[0].upper().startswith('O') else 'Under',
                    'line': re.sub(r'^[OU]\s*', '', totals[0], flags=re.I),
                    'odds': odds_numbers[1],
                    'confidence': 'medium',
                    'explanation': f'{totals[0]} samlede point til odds {odds_numbers[1]}',
                })
                if len(totals) > 1 and len(odds_numbers) >= 6:
                    event['markets'].append({
                        'market': 'total',
                        'selection': 'Over' if totals[1].upper().startswith('O') else 'Under',
                        'line': re.sub(r'^[OU]\s*', '', totals[1], flags=re.I),
                        'odds': odds_numbers[5],
                        'confidence': 'medium',
                        'explanation': f'{totals[1]} samlede point til odds {odds_numbers[5]}',
                    })

            if len(odds_numbers) >= 6:
                event['markets'].append({
                    'market': 'moneyline',
                    'selection': event['home'],
                    'line': None,
                    'odds': odds_numbers[2],
                    'confidence': 'medium',
                    'explanation': f'{event["home"]} vinder kampen til odds {odds_numbers[2]}',
                })
                event['markets'].append({
                    'market': 'moneyline',
                    'selection': event['away'],
                    'line': None,
                    'odds': odds_numbers[5],
                    'confidence': 'low',
                    'explanation': f'{event["away"]} vinder kampen til odds {odds_numbers[5]} (lav sikkerhed pga. OCR-layout)',
                })

            events.append(event)
            i += 2
        else:
            i += 1
    return events


def score_market(market):
    odds = market.get('odds')
    if odds is None:
        return 0
    confidence_bonus = {'high': 2, 'medium': 1, 'low': -2}.get(market.get('confidence'), 0)
    if market.get('market') == 'moneyline':
        base = 3 if 1.60 <= odds <= 3.50 else 1
    elif market.get('market') in {'handicap', 'total'}:
        base = 2 if 1.75 <= odds <= 2.10 else 1
    else:
        base = 0
    return base + confidence_bonus


def analyze_file(path):
    text = extract_text(path)
    lines = clean_lines(text)
    sport = infer_sport(lines)
    events = parse_basketball_like(lines)

    candidates = []
    for event in events:
        for market in event.get('markets', []):
            row = {
                'file': str(path),
                'sport': sport,
                'event': f'{event.get("home")} vs {event.get("away")}',
                'start_time_visible': event.get('start_time_visible'),
                **market,
            }
            row['score'] = score_market(row)
            candidates.append(row)

    candidates.sort(key=lambda x: (x.get('score', 0), x.get('odds') or 0), reverse=True)
    return {
        'file': str(path),
        'mtime': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'sport': sport,
        'line_count': len(lines),
        'events': events,
        'candidates': candidates,
        'raw_text_preview': text[:1500],
    }


def write_md(result):
    lines = [
        '# OCR POSSIBLE BETS ANALYSIS',
        '',
        f'Generated: {result["generated_at"]}',
        '',
        'Vigtigt: Dette er kun screenshot/OCR-parsing. Der beregnes ikke reel bookmaker-edge, fordi input kun er én bookmaker/ét skærmbillede.',
        '',
        f'Files analyzed: {result["files_analyzed"]}',
        '',
    ]

    all_candidates = []
    for item in result['files']:
        all_candidates.extend(item.get('candidates') or [])

    lines.append('## Bedste læsbare kandidater')
    if not all_candidates:
        lines.append('Ingen kandidater fundet.')
    for i, c in enumerate(sorted(all_candidates, key=lambda x: (x.get('score', 0), x.get('odds') or 0), reverse=True)[:20], 1):
        lines.extend([
            '',
            f'### {i}. {c.get("event")}',
            f'- Sport: {c.get("sport")}',
            f'- Synligt tidspunkt: {c.get("start_time_visible")}',
            f'- Marked: {c.get("market")}',
            f'- Spil: {c.get("selection")}' + (f' {c.get("line")}' if c.get('line') else ''),
            f'- Odds: {c.get("odds")}',
            f'- Sikkerhed: {c.get("confidence")}',
            f'- Forklaring: {c.get("explanation")}',
            f'- Score: {c.get("score")}',
        ])

    lines.append('\n## Filer')
    for item in result['files']:
        lines.extend([
            '',
            f'### {item.get("file")}',
            f'- Sport: {item.get("sport")}',
            f'- Linjer: {item.get("line_count")}',
            f'- Events: {len(item.get("events") or [])}',
        ])
        for event in item.get('events') or []:
            lines.append(f'  - {event.get("home")} vs {event.get("away")} ({event.get("start_time_visible")})')

    ANALYSIS_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    files = list_input_files()
    result = {
        'generated_at': now_iso(),
        'input_dir': str(INBOX),
        'files_analyzed': len(files),
        'files': [],
    }
    for p in files:
        try:
            result['files'].append(analyze_file(p))
        except Exception as exc:
            result['files'].append({'file': str(p), 'error': str(exc)[:500]})

    ANALYSIS_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    write_md(result)
    print(f'OCR possible bets parser OK | files={len(files)}')


if __name__ == '__main__':
    main()
