import json
import os
import pathlib
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ROOT = pathlib.Path('.')
INBOX = ROOT / 'inbox' / 'possible_bets'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

ANALYSIS_JSON = OUT / 'ocr_possible_bets_analysis.json'
ANALYSIS_MD = OUT / 'ocr_possible_bets_analysis.md'
FINAL_PICKS_JSON = OUT / 'ocr_final_picks.json'
FINAL_PICKS_MD = OUT / 'ocr_final_picks.md'

MAX_FILES = int(os.getenv('OCR_MAX_FILES', '25'))
FINAL_MAX_PICKS = int(os.getenv('OCR_FINAL_MAX_PICKS', '5'))
FINAL_MIN_ODDS = float(os.getenv('OCR_FINAL_MIN_ODDS', '1.55'))
FINAL_MAX_ODDS = float(os.getenv('OCR_FINAL_MAX_ODDS', '2.40'))
FINAL_ALLOW_DRAWS = os.getenv('OCR_FINAL_ALLOW_DRAWS', '0') == '1'
FINAL_CONFIDENCE = os.getenv('OCR_FINAL_CONFIDENCE', 'high')
FINAL_SOON_HOURS = float(os.getenv('OCR_FINAL_SOON_HOURS', '36'))
FINAL_MIN_START_MINUTES = float(os.getenv('OCR_FINAL_MIN_START_MINUTES', '0'))
DEFAULT_BANKROLL_DKK = float(os.getenv('OCR_BANKROLL_DKK', '100'))
MAX_TOTAL_STAKE_PCT = float(os.getenv('OCR_MAX_TOTAL_STAKE_PCT', '0.30'))
MIN_STAKE_DKK = float(os.getenv('OCR_MIN_STAKE_DKK', '1'))
MAX_STAKE_DKK = float(os.getenv('OCR_MAX_STAKE_DKK', '10'))
TIMEZONE = os.getenv('OCR_TIMEZONE', 'Europe/Copenhagen')
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
BALANCE_RE = re.compile(r'(\d+(?:[\.,]\d{2})?)\s*kr\.?', re.I)
SERVER_DATE_RE = re.compile(r'(\d{2})\.(\d{2})\.(\d{4}),\s*(\d{1,2})\.(\d{2})')
DK_WEEKDAYS = {'Man': 0, 'Tir': 1, 'Ons': 2, 'Tor': 3, 'Fre': 4, 'Lør': 5, 'Søn': 6}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def parse_iso_utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


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


def extract_bankroll_dkk(text):
    values = []
    for match in BALANCE_RE.finditer(str(text)):
        try:
            v = float(match.group(1).replace(',', '.'))
        except Exception:
            continue
        # Ignore phone numbers and huge unrelated numbers.
        if 1 <= v <= 100000:
            values.append(v)
    # On bet365 coupon, balance normally appears late and can be repeated. Use the last plausible DKK value.
    return values[-1] if values else None


def extract_capture_time(text):
    matches = list(SERVER_DATE_RE.finditer(str(text)))
    if not matches:
        return None
    m = matches[-1]
    day, month, year, hour, minute = map(int, m.groups())
    tz = ZoneInfo(TIMEZONE)
    return datetime(year, month, day, hour, minute, tzinfo=tz)


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

        odds = [parse_odds(x) for x in raw if is_decimal_odds_token(x)]
        n = len(event_rows)
        confidence = 'medium' if n >= 4 else 'high'
        method = 'football_1x2_column_major_decimal_only_long_section' if n >= 4 else 'football_1x2_column_major_decimal_only'

        if len(odds) >= n * 3:
            home_odds = odds[0:n]
            draw_odds = odds[n:n * 2]
            away_odds = odds[n * 2:n * 3]
            for idx, ev in enumerate(event_rows):
                assign_1x2_markets(ev, (home_odds[idx], draw_odds[idx], away_odds[idx]), confidence, method)
                ev['raw_section_odds'] = odds[:n * 3]
                ev['section_event_count'] = n
                events.append(ev)
            continue

        if n == 1 and len(odds) >= 3:
            ev = event_rows[0]
            assign_1x2_markets(ev, (odds[0], odds[1], odds[2]), 'medium', 'football_1x2_inline_decimal_fallback')
            ev['raw_section_odds'] = odds[:3]
            ev['section_event_count'] = n
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


def parse_visible_start(visible, reference_utc):
    if not visible:
        return None, None
    m = TIME_RE.fullmatch(str(visible).strip())
    if not m:
        return None, None
    day_name = m.group(1).title()
    clock = re.search(r'(\d{1,2}):(\d{2})', visible)
    if not clock or day_name not in DK_WEEKDAYS:
        return None, None
    hour, minute = int(clock.group(1)), int(clock.group(2))
    tz = ZoneInfo(TIMEZONE)
    ref_local = reference_utc.astimezone(tz)
    target_wd = DK_WEEKDAYS[day_name]
    delta_days = (target_wd - ref_local.weekday()) % 7
    candidate = (ref_local + timedelta(days=delta_days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate < ref_local - timedelta(minutes=30):
        candidate += timedelta(days=7)
    hours_until = (candidate.astimezone(timezone.utc) - reference_utc).total_seconds() / 3600
    return candidate.isoformat(), round(hours_until, 2)


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


def stake_pct_for_pick(pick):
    odds = pick.get('odds') or 0
    confidence = pick.get('confidence')
    if confidence != 'high':
        return 0.005
    if odds <= 1.80:
        return 0.020
    if odds <= 2.10:
        return 0.015
    return 0.010


def apply_stakes(picks, bankroll):
    if not picks:
        return picks
    total_cap = max(0, bankroll * MAX_TOTAL_STAKE_PCT)
    raw = []
    for p in picks:
        pct = stake_pct_for_pick(p)
        stake = bankroll * pct
        stake = max(MIN_STAKE_DKK, min(MAX_STAKE_DKK, stake))
        row = dict(p)
        row['stake_pct'] = pct
        row['stake_dkk_raw'] = round(stake, 2)
        raw.append(row)

    total_raw = sum(p['stake_dkk_raw'] for p in raw)
    scale = min(1.0, total_cap / total_raw) if total_raw > 0 else 1.0
    for p in raw:
        p['stake_dkk'] = round(max(MIN_STAKE_DKK, p['stake_dkk_raw'] * scale), 2)
        p['stake_note'] = f"Stake beregnet fra bankroll {bankroll:.2f} kr., pct {p['stake_pct']:.3f}, total cap {MAX_TOTAL_STAKE_PCT:.0%}."
    return raw


def make_final_picks(candidates, generated_at, bankroll):
    reference_utc = parse_iso_utc(generated_at)
    enriched = []
    for c in candidates:
        row = dict(c)
        start_iso, hours_until = parse_visible_start(row.get('start_time_visible'), reference_utc)
        row['start_datetime_local'] = start_iso
        row['hours_until_start'] = hours_until
        enriched.append(row)

    seen_events = set()
    picked = []
    rejected = []

    def sort_key(x):
        soon = x.get('hours_until_start')
        soon_sort = soon if soon is not None else 9999
        return (soon_sort, -(x.get('score', 0)), -(x.get('odds') or 0))

    for c in sorted(enriched, key=sort_key):
        reason = None
        odds = c.get('odds')
        hours_until = c.get('hours_until_start')
        if c.get('confidence') != FINAL_CONFIDENCE:
            reason = f"confidence_not_{FINAL_CONFIDENCE}"
        elif c.get('market') not in {'1x2', 'moneyline'}:
            reason = 'unsupported_market'
        elif c.get('line') == 'X' and not FINAL_ALLOW_DRAWS:
            reason = 'draws_disabled'
        elif odds is None or not (FINAL_MIN_ODDS <= odds <= FINAL_MAX_ODDS):
            reason = 'odds_outside_final_range'
        elif hours_until is None:
            reason = 'missing_or_unparsed_start_time'
        elif hours_until < FINAL_MIN_START_MINUTES / 60:
            reason = 'starts_too_soon_or_already_started'
        elif hours_until > FINAL_SOON_HOURS:
            reason = 'starts_too_late'
        elif c.get('event') in seen_events:
            reason = 'event_already_selected'

        if reason:
            rejected.append({**c, 'final_reject_reason': reason})
            continue

        row = dict(c)
        row['final_pick'] = True
        row['final_reason'] = f"Starter om ca. {hours_until} timer, {c.get('confidence')} confidence, odds {odds}, én pick pr kamp. Bemærk: ingen reel edge, kun bet365/PDF parsing."
        picked.append(row)
        seen_events.add(c.get('event'))
        if len(picked) >= FINAL_MAX_PICKS:
            break

    picked = apply_stakes(picked, bankroll)

    return {
        'rules': {
            'max_picks': FINAL_MAX_PICKS,
            'min_odds': FINAL_MIN_ODDS,
            'max_odds': FINAL_MAX_ODDS,
            'confidence': FINAL_CONFIDENCE,
            'allow_draws': FINAL_ALLOW_DRAWS,
            'one_pick_per_event': True,
            'soon_hours': FINAL_SOON_HOURS,
            'min_start_minutes': FINAL_MIN_START_MINUTES,
            'bankroll_dkk': bankroll,
            'max_total_stake_pct': MAX_TOTAL_STAKE_PCT,
            'min_stake_dkk': MIN_STAKE_DKK,
            'max_stake_dkk': MAX_STAKE_DKK,
            'note': 'Screenshot/PDF-only picks. No real bookmaker edge is calculated.',
        },
        'picks': picked,
        'rejected_sample': rejected[:80],
    }


def analyze_file(path):
    text = extract_text(path)
    lines = clean_lines(text)
    sport = infer_sport(lines)
    bankroll = extract_bankroll_dkk(text)
    capture_time = extract_capture_time(text)
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
                'section_event_count': event.get('section_event_count'),
                'source_bankroll_dkk': bankroll,
                'source_capture_time_local': capture_time.isoformat() if capture_time else None,
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
        'source_bankroll_dkk': bankroll,
        'source_capture_time_local': capture_time.isoformat() if capture_time else None,
        'events': events,
        'candidates': candidates,
        'raw_text_preview': text[:3500],
    }


def write_final_picks_md(final_picks, generated_at):
    lines = [
        '# OCR FINAL PICKS', '',
        f'Generated: {generated_at}', '',
        'Vigtigt: Dette er ikke value/edge-bets. Det er kun filtrerede, læsbare bet365/PDF-kandidater.', '',
        '## Regler',
        f'- Maks picks: {final_picks["rules"]["max_picks"]}',
        f'- Oddsrange: {final_picks["rules"]["min_odds"]}–{final_picks["rules"]["max_odds"]}',
        f'- Confidence: {final_picks["rules"]["confidence"]}',
        f'- Starter indenfor: {final_picks["rules"]["soon_hours"]} timer',
        f'- Uafgjort tilladt: {final_picks["rules"]["allow_draws"]}',
        f'- Én pick pr kamp: {final_picks["rules"]["one_pick_per_event"]}',
        f'- Bankroll: {final_picks["rules"]["bankroll_dkk"]:.2f} kr.',
        f'- Total stake cap: {final_picks["rules"]["max_total_stake_pct"]:.0%}',
        '',
        '## Final picks',
    ]
    if not final_picks['picks']:
        lines.append('Ingen final picks efter filteret.')
    total_stake = sum(p.get('stake_dkk', 0) for p in final_picks['picks'])
    if final_picks['picks']:
        lines.append(f'Samlet stake: {total_stake:.2f} kr.')
    for i, p in enumerate(final_picks['picks'], 1):
        lines.extend([
            '',
            f'### {i}. {p.get("event")}',
            f'- Liga: {p.get("league")}',
            f'- Tidspunkt: {p.get("start_time_visible")}',
            f'- Starter om: {p.get("hours_until_start")} timer',
            f'- Spil: {p.get("selection")}' + (f' ({p.get("line")})' if p.get('line') else ''),
            f'- Odds: {p.get("odds")}',
            f'- Stake: {p.get("stake_dkk")} kr.',
            f'- Confidence: {p.get("confidence")}',
            f'- Parser: {p.get("parse_method")}',
            f'- Begrundelse: {p.get("final_reason")}',
            f'- Stake-note: {p.get("stake_note")}',
        ])
    FINAL_PICKS_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_md(result):
    lines = [
        '# OCR/PDF POSSIBLE BETS ANALYSIS', '',
        f'Generated: {result["generated_at"]}', '',
        'Vigtigt: Screenshot/PDF parsing. Der beregnes ikke reel bookmaker-edge, fordi input kun er fra bet365.', '',
        f'Files analyzed: {result["files_analyzed"]}', '',
        '## Final picks',
    ]

    final_picks = result.get('final_picks') or {}
    picks = final_picks.get('picks') or []
    if not picks:
        lines.append('Ingen final picks efter filteret.')
    if picks:
        lines.append(f'Samlet stake: {sum(p.get("stake_dkk", 0) for p in picks):.2f} kr.')
    for i, p in enumerate(picks, 1):
        lines.extend([
            '',
            f'### {i}. {p.get("event")}',
            f'- Liga: {p.get("league")}',
            f'- Tidspunkt: {p.get("start_time_visible")}',
            f'- Starter om: {p.get("hours_until_start")} timer',
            f'- Spil: {p.get("selection")}' + (f' ({p.get("line")})' if p.get('line') else ''),
            f'- Odds: {p.get("odds")}',
            f'- Stake: {p.get("stake_dkk")} kr.',
            f'- Confidence: {p.get("confidence")}',
            f'- Begrundelse: {p.get("final_reason")}',
        ])

    all_candidates = []
    for item in result['files']:
        all_candidates.extend(item.get('candidates') or [])

    lines.append('\n## Bedste læsbare kandidater')
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
            f'- Kampe i sektion: {c.get("section_event_count")}',
            f'- Parser: {c.get("parse_method")}',
            f'- Forklaring: {c.get("explanation")}',
            f'- Score: {c.get("score")}',
        ])

    lines.append('\n## Filer')
    for item in result['files']:
        lines.extend(['', f'### {item.get("file")}', f'- Type: {item.get("type")}', f'- Sport: {item.get("sport")}', f'- Linjer: {item.get("line_count")}', f'- Bankroll fra fil: {item.get("source_bankroll_dkk")}', f'- Capture time: {item.get("source_capture_time_local")}', f'- Events: {len(item.get("events") or [])}', f'- Candidates: {len(item.get("candidates") or [])}'])
        for event in item.get('events') or []:
            lines.append(f'  - {event.get("league")}: {event.get("home")} vs {event.get("away")} ({event.get("start_time_visible")}) | section_count={event.get("section_event_count")}')
        if item.get('error'):
            lines.append(f'- Error: {item.get("error")}')
    ANALYSIS_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    generated_at = now_iso()
    files = list_input_files()
    result = {'generated_at': generated_at, 'input_dir': str(INBOX), 'accepted_extensions': sorted(ACCEPTED_EXTS), 'files_analyzed': len(files), 'files': []}
    for p in files:
        try:
            result['files'].append(analyze_file(p))
        except Exception as exc:
            result['files'].append({'file': str(p), 'type': file_type(p), 'error': str(exc)[:500]})

    all_candidates = []
    bankrolls = []
    for item in result['files']:
        all_candidates.extend(item.get('candidates') or [])
        if item.get('source_bankroll_dkk') is not None:
            bankrolls.append(item.get('source_bankroll_dkk'))
    bankroll = bankrolls[0] if bankrolls else DEFAULT_BANKROLL_DKK
    result['detected_bankroll_dkk'] = bankroll
    result['final_picks'] = make_final_picks(all_candidates, generated_at, bankroll)

    ANALYSIS_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    FINAL_PICKS_JSON.write_text(json.dumps({'generated_at': result['generated_at'], **result['final_picks']}, ensure_ascii=False, indent=2), encoding='utf-8')
    write_final_picks_md(result['final_picks'], result['generated_at'])
    write_md(result)
    print(f'OCR/PDF possible bets parser OK | files={len(files)} final_picks={len(result["final_picks"]["picks"])} bankroll={bankroll}')


if __name__ == '__main__':
    main()
