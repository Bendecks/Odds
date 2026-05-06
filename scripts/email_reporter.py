import os
import json
import pathlib
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

OUT = pathlib.Path('output')
ENGINE_JSON = OUT / 'v6_expansion_engine.json'
PAPER_JSON = OUT / 'paper_bets.json'
EMAIL_SUMMARY = OUT / 'email_reporter_summary.md'

MAIL_TO = os.getenv('MAIL_TO', '')
MAIL_FROM = os.getenv('MAIL_FROM', os.getenv('SMTP_USER', ''))
SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')


def parse_dt(v):
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except Exception:
        return datetime.max.replace(tzinfo=timezone.utc)


def load_json(path):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}


def top_bets(engine):
    bets = engine.get('top_bets') or []
    return sorted([b for b in bets if isinstance(b, dict)], key=lambda b: parse_dt(b.get('start')))


def open_bets(paper):
    bets = paper.get('bets') or []
    return sorted([b for b in bets if b.get('status') == 'open'], key=lambda b: parse_dt(b.get('start')))


def sport_dk(s):
    s = str(s or '')
    if 'soccer' in s: return 'Fodbold'
    if 'basketball' in s: return 'Basketball'
    if 'icehockey' in s: return 'Ishockey'
    if 'baseball' in s: return 'Baseball'
    if 'tennis' in s: return 'Tennis'
    if 'mma' in s: return 'MMA'
    if 'americanfootball' in s: return 'Amerikansk fodbold'
    return s or 'Ukendt sport'


def market_dk(m):
    m = str(m or '').lower()
    if m == 'h2h': return 'Kampvinder'
    if m == 'totals': return 'Over/under mål/point'
    if m == 'spreads': return 'Handicap/spread'
    return m or 'Ukendt marked'


def explain_pick(b):
    market = str(b.get('market') or '').lower()
    pick = str(b.get('pick') or '')
    point = b.get('point')
    event = b.get('event') or 'Ukendt kamp'

    if market == 'h2h':
        return f'Spillet er: {pick} vinder kampen i {event}.'

    if market == 'totals':
        direction = pick.lower()
        if direction == 'under':
            return f'Spillet er UNDER {point} samlede mål/point i {event}.'
        if direction == 'over':
            return f'Spillet er OVER {point} samlede mål/point i {event}.'

    if market == 'spreads':
        return f'Spillet er {pick} med handicap/spread {point} i {event}.'

    return f'Spillet er: {pick} i {event}.'


def bet_block(b, index=None, paper=False):
    prefix = f'BET {index}' if index is not None else 'BET'

    if paper:
        stake_line = f'Indsats: {b.get("paper_stake")} kr'
    else:
        stake_line = f'Foreslået indsats: {b.get("stake_kr")} kr'

    return '\n'.join([
        prefix,
        f'Kampstart: {b.get("start_local") or b.get("start")}',
        f'Sport: {sport_dk(b.get("sport"))}',
        f'Liga: {b.get("league")}',
        f'Kamp: {b.get("event")}',
        f'Marked: {market_dk(b.get("market"))}',
        explain_pick(b),
        f'Odds: {b.get("odds")}',
        stake_line,
        f'Edge: {b.get("edge_pct", "n/a")}% | Score: {b.get("pre_score", "n/a")}',
        f'Bookmakers: {b.get("books", "n/a")}',
        ''
    ])


def build_report(engine, paper):
    summary = paper.get('summary') if isinstance(paper.get('summary'), dict) else {}
    diagnostics = engine.get('diagnostics') if isinstance(engine.get('diagnostics'), dict) else {}

    lines = []
    lines.append('ODDS RAPPORT')
    lines.append('Sorteret efter kampstart. Alle spil er forklaret med almindelige ord.')
    lines.append('')

    lines.append('STATUS')
    lines.append(f'Åbne spil: {summary.get("open_count", 0)}')
    lines.append(f'Åben eksponering: {summary.get("open_stake", 0)} / {summary.get("max_open_exposure_kr", 0)} kr')
    lines.append(f'Profit: {summary.get("profit", 0)} kr')
    lines.append(f'ROI: {summary.get("roi_pct", 0)}%')
    lines.append(f'Hitrate: {summary.get("hitrate_pct", 0)}%')
    lines.append('')

    lines.append('ENGINE STATUS')
    lines.append(f'Mode: {engine.get("mode")}')
    lines.append(f'Summary: {engine.get("summary")}')
    lines.append(f'Kandidater fundet: {diagnostics.get("candidate_count", 0)}')
    lines.append(f'Ligaer scannet: {diagnostics.get("leagues_total", 0)}')
    lines.append(f'Events fundet: {diagnostics.get("event_count", 0)}')
    lines.append(f'Kommende events: {diagnostics.get("upcoming_event_count", 0)}')
    lines.append(f'Filtrerede ligaer: {diagnostics.get("league_filtered", 0)}')
    lines.append(f'Edge-filtrerede picks: {diagnostics.get("edge_filtered", 0)}')
    lines.append(f'Odds-fejl: {diagnostics.get("odds_errors", 0)}')
    lines.append('')

    lines.append('NYE/TOP PICKS')
    lines.append('')

    top = top_bets(engine)
    if not top:
        lines.append('Ingen valide bets fundet i dette run.')
        lines.append('')

    for i, b in enumerate(top[:20], 1):
        lines.append(bet_block(b, i, paper=False))

    lines.append('ÅBNE PAPER BETS')
    lines.append('')

    open_list = open_bets(paper)
    if not open_list:
        lines.append('Ingen åbne paper bets.')
        lines.append('')

    for i, b in enumerate(open_list[:30], 1):
        lines.append(bet_block(b, i, paper=True))

    return '\n'.join(lines)


def send_email(body):
    if not all([MAIL_TO, MAIL_FROM, SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        raise RuntimeError('Missing SMTP/email configuration')

    msg = MIMEMultipart()
    msg['Subject'] = 'Odds rapport - forklaret'
    msg['From'] = MAIL_FROM
    msg['To'] = MAIL_TO
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(MAIL_FROM, MAIL_TO, msg.as_string())


def main():
    engine = load_json(ENGINE_JSON)
    paper = load_json(PAPER_JSON)
    body = build_report(engine, paper)
    send_email(body)
    EMAIL_SUMMARY.write_text(body, encoding='utf-8')
    print('Email report sent')


if __name__ == '__main__':
    main()
