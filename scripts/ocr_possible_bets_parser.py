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
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp'}
TEXT_EXTS = {'.txt', '.json', '.md'}
PDF_EXTS = {'.pdf'}
ACCEPTED_EXTS = TEXT_EXTS.union(IMAGE_EXTS).union(PDF_EXTS)

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

PROMO_WORDS = {
    'TIDLIG UDBETALING',
    'AKKUMULATOR PÅ FLERE SPORTSGRENE',
}

NOISE_PATTERNS = [
    r'^bet$', r'^365$', r'^bet365$', r'^bet365\.dk$', r'^Session ', r'^Ansvarsfuldt spil$',
    r'^ÅBN$', r'^Åbn i appen', r'^Sport$', r'^Live$', r'^Casino$', r'^Væddemål$',
    r'^AKKUMULATOR', r'^Matchkupon$', r'^Ekstra$', r'^Alle$', r'^Alle kampe$', r'^Næste ',
    r'^Hjem$', r'^<$', r'^=$', r'^•', r'^\.\.$', r'^Information og forsinkelser',
    r'^Indstillinger$', r'^Tilbud$', r'^Åbningstilbud$', r'^Lyd$', r'^Statistik$',
    r'^Resultater$', r'^Livescore Resultater$', r'^Hjælp$', r'^Indbetalinger Udbetalinger$',
    r'^Regler', r'^Sider$', r'^Nyheder$', r'^Jobs$', r'^Partnere$', r'^Sprog$',
    r'^Server Tid', r'^Side \d+ af \d+$', r'^07\.05\.2026',
]

DAY_RE = r'(Man|Tir|Ons|Tor|Fre|Lør|Søn)'
TIME_RE = re.compile(rf'^{DAY_RE}\s+\d{{1,2}}:\d{{2}}(?:\s+\d+)?$', re.I)
SCORE_RE = re.compile(r'^\(\d+\)$')
COUNT_RE = re.compile(r'^\d+»?$')
HEADER_1X2_RE = re.compile(r'\b1\s+X\s+2\b', re.I)
DECIMAL_ODDS_RE = re.compile(r'^\d{1,2}[\.,]\d{2}$')


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
        if p.is_file() and p.suffix.lower() in ACCEPTED_EXTS:
            files.append(p)
    files.sort(key=lambda p: p.name, reverse=True)
    return files[:MAX_FILES]


def ocr_image(path):
    try:
        from PIL import Image, ImageOps, ImageFilter
        import pytesseract
    except Exception as exc:
        raise RuntimeError(f'OCR dependencies missing. Install pillow, pytesseract and tesseract-ocr. {exc}')

    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    w, h = img.size
    if w < 1400:
        scale = 1400 / max(w, 1)
        img = img.resize((int(w * scale), int(h * scale)))
    img = img.filter(ImageFilter.SHARPEN)
    return pytesseract.image_to_string(img, config='--psm 6')


def extract_pdf_text(path):
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError(f'PDF dependency missing. Install pypdf. {exc}')

    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or '')
    return '\n'.join(parts)


def extract_text(path):
    suffix = path.suffix.lower()
    if suffix in PDF_EXTS:
        return extract_pdf_text(path)
    if suffix in IMAGE_EXTS:
        return ocr_image(path)

    raw = read_text_file(path)
    if suffix == '.json':
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


def is_decimal_odds_token(x):
    """For football 1X2 PDFs: accept prices like 1.70, but reject count markers like 6 or 5."""
    return bool(DECIMAL_ODDS_RE.fullmatch(str(x).strip())) and is_odds(x)


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
    return bool(TIME_RE.fullmatch(str(x))) or bool(re.fullmatch(r'\d{1,2}:\d{2}', str(x)))


def looks_like_team(x):
    x = str(x).strip()
    if is_odds(x) or is_handicap(x) or is_total_line(x) or looks_like_time(x):
        return False
    if SCORE_RE.fullmatch(x) or COUNT_RE.fullmatch(x):
        return False
    if len(x) < 2 or len(x) > 55:
        return False
    if x in PROMO_WORDS:
        return False
    if HEADER_1X2_RE.search(x):
        return False
    if re.search(r'[A-Za-zÆØÅæøå]', x) and not re.search(r'^(Handicap|Total|Point|Rebounds|Assist|Lige På|Point O/U|Fuldtid|Kvalificerer|Total antal mål|Begge hold scorer)$', x, flags=re.I):
        return True
    return False


def normalize_team(x):
    return TEAM_ALIASES.get(x, x)


def infer_sport(lines):
    sport = 'unknown'
    joined = ' '.join(lines).lower()
    if 'fodbold' in joined or 'uefa' in joined or 'superligaen' in joined:
        return 'football'
    for line in lines:
        if line in SPORT_WORDS:
            sport = SPORT_WORDS[line]
    return sport


def is_league_header(line):
    x = str(line).strip()
    if HEADER_1X2_RE.search(x):
        return True
    if re.search(r'(League|Liga|division|Superligaen|Eliteserien|Allsvenskan|Libertadores|Sudamericana|UEFA|Conference)', x, flags=re.I):
        return not is_odds(x) and not looks_like_time(x)
    return False


def clean_league_name(line):
    return HEADER_1X2_RE.sub('', line).strip(' -') or line


def assign_1x2_markets(ev, odds_triplet, confidence, method):
    home_odds, draw_odds, away_odds = odds_triplet
    ev['markets'] = [
        {'market': '1x2', 'selection': ev['home'], 'line': '1', 'odds': home_odds, 'confidence': confidence, 'explanation': f'{ev["home"]} vinder til odds {home_odds}'},
        {'market': '1x2', 'selection': 'Draw', 'line': 'X', 'odds': draw_odds, 'confidence': confidence, 'explanation': f'Uafgjort til odds {draw_odds}'},
        {'market': '1x2', 'selection': ev['away'], 'line': '2', 'odds': away_odds, 'confidence': confidence, 'explanation': f'{ev["away"]} vinder til odds {away_odds}'},
    ]
    ev['parse_method'] = method
    return ev


def parse_football_1x2_sections(lines):
    events = []
    sections = []
    current = None

    for line in lines:
        if line in PROMO_WORDS:
            continue
        if is_league_header(line):
            if current:
                sections.append(current)
            current = {'league': clean_league_name(line), 'lines': []}
        elif current:
            current['lines'].append(line)
    if current:
        sections.append(current)

    for section in sections:
        league = section['league']
        raw = [x for x in section['lines'] if x not in PROMO_WORDS]
        event_rows = []
        i = 0
        while i < len(raw) - 2:
            home, away, t = raw[i], raw[i + 1], raw[i + 2]
            if looks_like_team(home) and looks_like_team(away) and looks_like_time(t):
                event_rows.append({
                    'league': league,
                    'home': normalize_team(home),
                    'away': normalize_team(away),
                    'start_time_visible': t,
                    'raw_home': home,
                    'raw_away': away,
                })
                i += 3
                continue
            i += 1

        if not event_rows:
            continue

        # Only decimal price tokens count as football 1X2 odds. This rejects bet365 side counts like "6" and scores like "(0)".
        odds = [parse_odds(x) for x in raw if is_decimal_odds_token(x)]
        n = len(event_rows)

        if len(odds) >= n * 3:
            home_odds = odds[0:n]
            draw_odds = odds[n:n * 2]
            away_odds = odds[n * 2:n * 3]
            for idx, ev in enumerate(event_rows):
                assign_1x2_markets(ev, (home_odds[idx], draw_odds[idx], away_odds[idx]), 'high', 'football_1x2_column_major_decimal_only')
                ev['raw_section_odds'] = odds[:n * 3]
                events.append(ev)
            continue

        if n == 1 and len(odds) >= 3:
            ev = event_rows[0]
            assign_1x2_markets(ev, (odds[0], odds[1], odds[2]), 'medium', 'football_1x2_inline_decimal_fallback')
            ev['raw_section_odds'] = odds[:3]
            events.append(ev)

    return events


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

        chunk = lines[i + 2:i + 16]
        odds_numbers = [parse_odds(x) for x in chunk if is_odds(x)]
        handicaps = [x for x in chunk if is_handicap(x)]
        totals = [x for x in chunk if is_total_line(x)]
        times = [x for x in chunk if looks_like_time(x)]

        if len(odds_numbers) >= 2 and (handicaps or totals or times):
            event = {
                'league': None,
                'home': normalize_team(home),
                'away': normalize_team(away),
                'raw_home': home,
                'raw_away': away,
                'start_time_visible': times[0] if times else None,
                'markets': [],
                'raw_chunk': chunk,
                'parse_method': 'basketball_like',
            }

            if handicaps and len(odds_numbers) >= 2:
                event['markets'].append({'market': 'handicap', 'selection': event['home'], 'line': handicaps[0], 'odds': odds_numbers[0], 'confidence': 'medium', 'explanation': f'{event["home"]} får handicap {handicaps[0]} til odds {odds_numbers[0]}'})
                if len(handicaps) > 1 and len(odds_numbers) >= 5:
                    event['markets'].append({'market': 'handicap', 'selection': event['away'], 'line': handicaps[1], 'odds': odds_numbers[4], 'confidence': 'medium', 'explanation': f'{event["away"]} får handicap {handicaps[1]} til odds {odds_numbers[4]}'})

            if totals and len(odds_numbers) >= 4:
                event['markets'].append({'market': 'total', 'selection': 'Over' if totals[0].upper().startswith('O') else 'Under', 'line': re.sub(r'^[OU]\s*', '', totals[0], flags=re.I), 'odds': odds_numbers[1], 'confidence': 'medium', 'explanation': f'{totals[0]} samlede point til odds {odds_numbers[1]}'})
                if len(totals) > 1 and len(odds_numbers) >= 6:
                    event['markets'].append({'market': 'total', 'selection': 'Over' if totals[1].upper().startswith('O') else 'Under', 'line': re.sub(r'^[OU]\s*', '', totals[1], flags=re.I), 'odds': odds_numbers[5], 'confidence': 'medium', 'explanation': f'{totals[1]} samlede point til odds {odds_numbers[5]}'})

            if len(odds_numbers) >= 6:
                event['markets'].append({'market': 'moneyline', 'selection': event['home'], 'line': None, 'odds': odds_numbers[2], 'confidence': 'medium', 'explanation': f'{event["home"]} vinder kampen til odds {odds_numbers[2]}'})
                event['markets'].append({'market': 'moneyline', 'selection': event['away'], 'line': None, 'odds': odds_numbers[5], 'confidence': 'low', 'explanation': f'{event["away"]} vinder kampen til odds {odds_numbers[5]} (lav sikkerhed pga. OCR-layout)'})

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
    if market.get('market') in {'moneyline', '1x2'}:
        if market.get('line') == 'X':
            base = 1
        else:
            base = 3 if 1.55 <= odds <= 3.50 else 1
    elif market.get('market') in {'handicap', 'total'}:
        base = 2 if 1.75 <= odds <= 2.10 else 1
    else:
        base = 0
    return base + confidence_bonus


def file_type(path):
    suffix = path.suffix.lower()
    if suffix in PDF_EXTS:
        return 'pdf_text'
    if suffix in IMAGE_EXTS:
        return 'image_ocr'
    return 'text'


def analyze_file(path):
    text = extract_text(path)
    lines = clean_lines(text)
    sport = infer_sport(lines)
    football_events = parse_football_1x2_sections(lines)
    basketball_events = [] if football_events else parse_basketball_like(lines)
    events = football_events + basketball_events

    candidates = []
    seen = set()
    for event in events:
        for market in event.get('markets', []):
            key = (event.get('home'), event.get('away'), event.get('start_time_visible'), market.get('market'), market.get('selection'), market.get('line'))
            if key in seen:
                continue
            seen.add(key)
            row = {
                'file': str(path),
                'sport': sport,
                'league': event.get('league'),
                'event': f'{event.get("home")} vs {event.get("away")}',
                'start_time_visible': event.get('start_time_visible'),
                'parse_method': event.get('parse_method'),
                **market,
            }
            row['score'] = score_market(row)
            candidates.append(row)

    candidates.sort(key=lambda x: (x.get('score', 0), x.get('odds') or 0), reverse=True)
    return {
        'file': str(path),
        'type': file_type(path),
        'mtime': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'sport': sport,
        'line_count': len(lines),
        'events': events,
        'candidates': candidates,
        'raw_text_preview': text[:3500],
    }


def write_md(result):
    lines = [
        '# OCR/PDF POSSIBLE BETS ANALYSIS', '',
        f'Generated: {result["generated_at"]}', '',
        'Vigtigt: Screenshot/PDF parsing. Der beregnes ikke reel bookmaker-edge, fordi input kun er fra bet365.', '',
        f'Files analyzed: {result["files_analyzed"]}', '',
    ]

    all_candidates = []
    for item in result['files']:
        all_candidates.extend(item.get('candidates') or [])

    lines.append('## Bedste læsbare kandidater')
    if not all_candidates:
        lines.append('Ingen kandidater fundet.')
    for i, c in enumerate(sorted(all_candidates, key=lambda x: (x.get('score', 0), x.get('odds') or 0), reverse=True)[:40], 1):
        lines.extend([
            '',
            f'### {i}. {c.get("event")}',
            f'- Liga: {c.get("league")}',
            f'- Sport: {c.get("sport")}',
            f'- Synligt tidspunkt: {c.get("start_time_visible")}',
            f'- Marked: {c.get("market")}',
            f'- Spil: {c.get("selection")}' + (f' ({c.get("line")})' if c.get('line') else ''),
            f'- Odds: {c.get("odds")}',
            f'- Sikkerhed: {c.get("confidence")}',
            f'- Parser: {c.get("parse_method")}',
            f'- Forklaring: {c.get("explanation")}',
            f'- Score: {c.get("score")}',
        ])

    lines.append('\n## Filer')
    for item in result['files']:
        lines.extend(['', f'### {item.get("file")}', f'- Type: {item.get("type")}', f'- Sport: {item.get("sport")}', f'- Linjer: {item.get("line_count")}', f'- Events: {len(item.get("events") or [])}', f'- Candidates: {len(item.get("candidates") or [])}'])
        for event in item.get('events') or []:
            lines.append(f'  - {event.get("league")}: {event.get("home")} vs {event.get("away")} ({event.get("start_time_visible")})')
        if item.get('error'):
            lines.append(f'- Error: {item.get("error")}')
    ANALYSIS_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    files = list_input_files()
    result = {'generated_at': now_iso(), 'input_dir': str(INBOX), 'accepted_extensions': sorted(ACCEPTED_EXTS), 'files_analyzed': len(files), 'files': []}
    for p in files:
        try:
            result['files'].append(analyze_file(p))
        except Exception as exc:
            result['files'].append({'file': str(p), 'type': file_type(p), 'error': str(exc)[:500]})

    ANALYSIS_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    write_md(result)
    print(f'OCR/PDF possible bets parser OK | files={len(files)}')


if __name__ == '__main__':
    main()
