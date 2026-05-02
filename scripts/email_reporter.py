import os
import json
import pathlib
import smtplib
import ssl
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
        return datetime.fromisoformat(str(v).replace('Z','+00:00'))
    except Exception:
        return datetime.max.replace(tzinfo=timezone.utc)


def load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def top_bets(engine):
    bets = engine.get('top_bets') or []
    return sorted(bets, key=lambda b: parse_dt(b.get('start')))


def open_bets(paper):
    bets = paper.get('bets') or []
    return sorted([b for b in bets if b.get('status')=='open'], key=lambda b: parse_dt(b.get('start')))


def build_report(engine, paper):
    lines = []
    lines.append('ODDS REPORT (SORTED)')
    lines.append('')

    lines.append('TOP PICKS:')
    for b in top_bets(engine)[:20]:
        lines.append(f"{b.get('start_local')} | {b.get('event')} | {b.get('pick')} | odds {b.get('odds')} | units {b.get('stake_kr')}")

    lines.append('')
    lines.append('OPEN BETS:')
    for b in open_bets(paper)[:30]:
        lines.append(f"{b.get('start_local')} | {b.get('event')} | {b.get('pick')} | {b.get('paper_stake')} kr ({b.get('stake_units')}u)")

    return '\n'.join(lines)


def send_email(body):
    msg = MIMEMultipart()
    msg['Subject'] = 'Odds Report'
    msg['From'] = MAIL_FROM
    msg['To'] = MAIL_TO
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(MAIL_FROM, MAIL_TO, msg.as_string())


def main():
    engine = load_json(ENGINE_JSON)
    paper = load_json(PAPER_JSON)
    body = build_report(engine, paper)
    send_email(body)
    EMAIL_SUMMARY.write_text(body)

if __name__ == '__main__':
    main()
