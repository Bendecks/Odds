import json
import os
import pathlib
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path('.')
INBOX = ROOT / 'inbox' / 'possible_bets'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
ANALYSIS_JSON = OUT / 'ocr_possible_bets_analysis.json'
ANALYSIS_MD = OUT / 'ocr_possible_bets_analysis.md'

MAX_FILES = int(os.getenv('OCR_MAX_FILES', '25'))
TIMEZONE_NAME = os.getenv('OCR_TIMEZONE', 'Europe/Copenhagen')
DECIMAL_ODDS_RE = re.compile(r'^\d{1,2}[\.,]\d{2}$')
TIME_ONLY_RE = re.compile(r'^\d{1,2}:\d{2}$')
DATE_HEADER_RE = re.compile(r'^(Man|Tir|Ons|Tor|Fre|Lør|Søn)\s+\d{2}\s+\w+\s+1\s+X\s+2$', re.I)
CAPTURE_DATE_RE = re.compile(r'(\d{2})\.(\d{2})\.(\d{4}),\s*(\d{1,2})[\.:](\d{2})')
BALANCE_RE = re.compile(r'(\d+(?:[\.,]\d{2})?)\s*kr\.?', re.I)
DK_WEEKDAY_BY_DATE = ['Man', 'Tir', 'Ons', 'Tor', 'Fre', 'Lør', 'Søn']
NOISE = {
    'Information og forsinkelser i udsendelsen', 'Indstillinger', 'Tilbud', 'Åbningstilbud', 'Lyd',
    'Fodbold', 'Statistik', 'Fodbold Sport', 'Resultater', 'Livescore Resultater', 'Hjælp',
    'Indbetalinger Udbetalinger', 'Regler og Vilkår Tekniske problemer', 'Ansvarsfuldt spil Regler om fortrolighed',
    'Regler om cookies Klageprocedure', 'Regler', 'Sider', 'Nyheder Jobs', 'Partnere', 'Sprog',
    'Hjem Sport Live Væddemål Casino', 'KOMMENDE KAMPE Se alle', 'Bedste ligaer', 'Danmark', 'Norge',
    'Populære Turneringer Vindere Afgørelsesfunktioner', 'bet365 FAQ Kontakt os'
}
BAD_PREFIXES = ('© ', 'Ved at besøge', 'Denne side er beskyttet', 'StopSpillet', 'Du kan ', 'bet365 er ', 'Server Tid', 'Session ')


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def pdf_text(path):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return '\n'.join((page.extract_text() or '') for page in reader.pages)


def is_decimal_odds(x):
    return bool(DECIMAL_ODDS_RE.fullmatch(str(x).strip()))


def parse_float(x):
    return float(str(x).replace(',', '.'))


def is_time(x):
    return bool(TIME_ONLY_RE.fullmatch(str(x).strip()))


def looks_like_team(x):
    x = str(x).strip()
    if not x or len(x) < 2 or len(x) > 60:
        return False
    if x in NOISE or x.startswith(BAD_PREFIXES):
        return False
    if is_time(x) or is_decimal_odds(x):
        return False
    if DATE_HEADER_RE.fullmatch(x):
        return False
    if re.fullmatch(r'\d+\s+kampe', x, re.I):
        return False
    if re.search(r'1\s+X\s+2', x, re.I):
        return False
    if re.search(r'[A-Za-zÆØÅæøå]', x):
        return True
    return False


def clean_and_expand_lines(text):
    out = []
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        if line in NOISE or line.startswith(BAD_PREFIXES):
            continue
        # Split lines that are pure odds triples: "1.75 4.20 3.80".
        parts = line.split()
        if len(parts) == 3 and all(is_decimal_odds(p) for p in parts):
            out.extend(parts)
            continue
        out.append(line)
    return out


def extract_bankroll(text):
    vals = []
    for m in BALANCE_RE.finditer(str(text)):
        try:
            v = parse_float(m.group(1))
            if 1 <= v <= 100000:
                vals.append(v)
        except Exception:
            pass
    return vals[-1] if vals else None


def extract_capture_time(text):
    matches = list(CAPTURE_DATE_RE.finditer(str(text)))
    if not matches:
        return None
    m = matches[-1]
    d, mo, y, h, mi = map(int, m.groups())
    return datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(TIMEZONE_NAME))


def visible_time(time_str, capture_time):
    if not capture_time:
        return time_str
    wd = DK_WEEKDAY_BY_DATE[capture_time.weekday()]
    return f'{wd} {time_str}'


def add_markets(ev, odds):
    home_odds, draw_odds, away_odds = odds
    ev['markets'] = [
        {'market': '1x2', 'selection': ev['home'], 'line': '1', 'odds': home_odds, 'confidence': 'high', 'explanation': f'{ev["home"]} vinder til odds {home_odds}'},
        {'market': '1x2', 'selection': 'Draw', 'line': 'X', 'odds': draw_odds, 'confidence': 'high', 'explanation': f'Uafgjort til odds {draw_odds}'},
        {'market': '1x2', 'selection': ev['away'], 'line': '2', 'odds': away_odds, 'confidence': 'high', 'explanation': f'{ev["away"]} vinder til odds {away_odds}'},
    ]
    return ev


def parse_inline_events(lines, capture_time):
    events = []
    i = 0
    while i <= len(lines) - 6:
        home, away, t = lines[i], lines[i + 1], lines[i + 2]
        o1, ox, o2 = lines[i + 3], lines[i + 4], lines[i + 5]
        if looks_like_team(home) and looks_like_team(away) and is_time(t) and all(is_decimal_odds(x) for x in (o1, ox, o2)):
            ev = {
                'league': 'bet365_full_page_inline',
                'home': home,
                'away': away,
                'raw_home': home,
                'raw_away': away,
                'start_time_visible': visible_time(t, capture_time),
                'parse_method': 'football_1x2_inline_row_pdf',
                'section_event_count': 1,
                'raw_section_odds': [parse_float(o1), parse_float(ox), parse_float(o2)],
            }
            add_markets(ev, ev['raw_section_odds'])
            events.append(ev)
            i += 6
        else:
            i += 1
    return events


def implied_score(market):
    odds = market.get('odds') or 0
    if market.get('line') == 'X':
        return 1
    return 5 if 1.55 <= odds <= 2.10 else 2


def candidates_from_events(path, events, bankroll, capture_time):
    rows = []
    seen = set()
    for ev in events:
        for m in ev.get('markets', []):
            key = (ev['home'], ev['away'], ev['start_time_visible'], m['line'])
            if key in seen:
                continue
            seen.add(key)
            row = {
                'file': str(path),
                'sport': 'football',
                'league': ev.get('league'),
                'event': f'{ev["home"]} vs {ev["away"]}',
                'start_time_visible': ev.get('start_time_visible'),
                'parse_method': ev.get('parse_method'),
                'section_event_count': ev.get('section_event_count'),
                'source_bankroll_dkk': bankroll,
                'source_capture_time_local': capture_time.isoformat() if capture_time else None,
                **m,
            }
            row['score'] = implied_score(row)
            rows.append(row)
    return rows


def analyze_pdf(path):
    text = pdf_text(path)
    lines = clean_and_expand_lines(text)
    bankroll = extract_bankroll(text)
    capture_time = extract_capture_time(text)
    events = parse_inline_events(lines, capture_time)
    return {
        'file': str(path),
        'type': 'pdf_text_inline_reparse',
        'mtime': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'sport': 'football',
        'line_count': len(lines),
        'source_bankroll_dkk': bankroll,
        'source_capture_time_local': capture_time.isoformat() if capture_time else None,
        'events': events,
        'candidates': candidates_from_events(path, events, bankroll, capture_time),
        'raw_text_preview': text[:3500],
    }


def write_md(result):
    lines = [
        '# OCR/PDF POSSIBLE BETS ANALYSIS — INLINE REPARSE', '',
        f'Generated: {result["generated_at"]}', '',
        f'Files analyzed: {result["files_analyzed"]}', '',
        '## Parsed events',
    ]
    for item in result['files']:
        lines.extend(['', f'### {item["file"]}', f'- Events: {len(item.get("events") or [])}', f'- Candidates: {len(item.get("candidates") or [])}', f'- Bankroll: {item.get("source_bankroll_dkk")}'])
        for ev in item.get('events') or []:
            odds = ev.get('raw_section_odds') or []
            lines.append(f'- {ev.get("start_time_visible")}: {ev.get("home")} vs {ev.get("away")} — {odds}')
    ANALYSIS_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    files = sorted([p for p in INBOX.rglob('*.pdf') if p.is_file()], key=lambda p: p.name, reverse=True)[:MAX_FILES] if INBOX.exists() else []
    result = {
        'generated_at': now_iso(),
        'input_dir': str(INBOX),
        'parser': 'ocr_inline_football_reparser',
        'files_analyzed': len(files),
        'files': [],
    }
    bankrolls = []
    for p in files:
        try:
            item = analyze_pdf(p)
            result['files'].append(item)
            if item.get('source_bankroll_dkk') is not None:
                bankrolls.append(item['source_bankroll_dkk'])
        except Exception as exc:
            result['files'].append({'file': str(p), 'type': 'pdf_text_inline_reparse', 'error': str(exc)[:500]})
    if bankrolls:
        result['detected_bankroll_dkk'] = bankrolls[0]
    ANALYSIS_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    write_md(result)
    total_events = sum(len(x.get('events') or []) for x in result['files'])
    print(f'Inline football reparser OK | files={len(files)} events={total_events}')


if __name__ == '__main__':
    main()
