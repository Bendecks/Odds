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
ENGINE_MD = OUT / 'v6_expansion_engine.md'
PAPER_MD = OUT / 'paper_summary.md'
AUTO_SETTLER_MD = OUT / 'paper_auto_settler_summary.md'
EMAIL_STATE = OUT / 'email_reporter_state.json'
EMAIL_SUMMARY = OUT / 'email_reporter_summary.md'

MAIL_TO = os.getenv('MAIL_TO', '').strip()
MAIL_FROM = os.getenv('MAIL_FROM', os.getenv('SMTP_USER', '')).strip()
SMTP_HOST = os.getenv('SMTP_HOST', '').strip()
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '').strip()
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '').strip()
SEND_MODE = os.getenv('EMAIL_SEND_MODE', 'daily_or_new').strip().lower()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def read_text(path, fallback=''):
    try:
        if path.exists():
            return path.read_text(encoding='utf-8')
    except Exception:
        pass
    return fallback


def money(v):
    try:
        return f"{float(v):.2f}"
    except Exception:
        return str(v)


def latest_open_bets(paper, limit=25):
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    return [b for b in bets if b.get('status') == 'open'][-limit:]


def latest_settled_bets(paper, limit=15):
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    return [b for b in bets if b.get('status') == 'settled'][-limit:]


def top_bets(engine, limit=20):
    bets = engine.get('top_bets') if isinstance(engine.get('top_bets'), list) else []
    return bets[:limit]


def fingerprint(engine, paper):
    parts = []
    for b in top_bets(engine, 30):
        parts.append('|'.join([str(b.get('event')), str(b.get('start_local') or b.get('start')), str(b.get('market')), str(b.get('pick')), str(b.get('odds'))]))
    summary = paper.get('summary') if isinstance(paper.get('summary'), dict) else {}
    parts.append(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return str(hash('\n'.join(parts)))


def should_send(engine, paper, state):
    fp = fingerprint(engine, paper)
    last_fp = state.get('last_fingerprint')
    last_sent_day = state.get('last_sent_day')
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if SEND_MODE == 'always':
        return True, fp, 'always'
    if SEND_MODE == 'new_only' and fp != last_fp:
        return True, fp, 'new_data'
    if SEND_MODE == 'daily_or_new':
        if fp != last_fp:
            return True, fp, 'new_data'
        if last_sent_day != today:
            return True, fp, 'daily_digest'
    return False, fp, 'no_change'


def build_report(engine, paper):
    summary = paper.get('summary') if isinstance(paper.get('summary'), dict) else {}
    mode = engine.get('mode', 'unknown')
    diag = engine.get('diagnostics') if isinstance(engine.get('diagnostics'), dict) else {}
    risk = engine.get('risk_counts') if isinstance(engine.get('risk_counts'), dict) else {}

    lines = []
    lines.append('ODDS PAPER REPORT')
    lines.append(f'Generated: {now_iso()}')
    lines.append(f'Engine: {mode}')
    lines.append('')
    lines.append('PERFORMANCE')
    lines.append(f"Open bets: {summary.get('open_count', 0)}")
    lines.append(f"Settled: {summary.get('settled_count', 0)}")
    lines.append(f"Won/Lost/Push: {summary.get('won', 0)} / {summary.get('lost', 0)} / {summary.get('push_void', summary.get('push', 0))}")
    lines.append(f"Profit: {money(summary.get('profit', 0))}")
    lines.append(f"ROI: {summary.get('roi_pct', 0)}%")
    lines.append(f"Hitrate: {summary.get('hitrate_pct', 0)}%")
    lines.append('')
    lines.append('ENGINE STATUS')
    lines.append(f"Candidates: {engine.get('candidate_count', 'n/a')}")
    lines.append(f"Top eligible: {diag.get('top_eligible_count', 'n/a')}")
    lines.append(f"Unique games: {diag.get('unique_games', 'n/a')}")
    lines.append(f"Risk moved to watchlist: {diag.get('risk_moved_to_watchlist', 'n/a')}")
    if risk:
        lines.append(f"Risk counts: {json.dumps(risk, ensure_ascii=False)}")
    lines.append('')
    lines.append('TODAY / LATEST TOP PICKS')
    tb = top_bets(engine, 20)
    if not tb:
        lines.append('No top picks found.')
    for i, b in enumerate(tb, 1):
        lines.append(f"{i}. {b.get('event')} | {b.get('start_local') or b.get('start')} | {b.get('sport')} | {b.get('market')} | {b.get('pick')} {b.get('point')} | odds {b.get('odds')} | stake {b.get('stake_kr')} | edge {b.get('edge_pct')} | score {b.get('pre_score')}")
    lines.append('')
    lines.append('OPEN PAPER BETS')
    obs = latest_open_bets(paper, 25)
    if not obs:
        lines.append('No open paper bets.')
    for b in obs:
        lines.append(f"- {b.get('id')} | {b.get('start_local') or b.get('start')} | {b.get('sport')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} {b.get('point')} | odds {b.get('odds')} | stake {b.get('paper_stake')}")
    lines.append('')
    lines.append('RECENT SETTLED')
    settled = latest_settled_bets(paper, 15)
    if not settled:
        lines.append('No settled bets yet.')
    for b in settled:
        lines.append(f"- {b.get('id')} | {b.get('result')} | profit {b.get('profit')} | {b.get('event')} | {b.get('pick')} @ {b.get('odds')} | {b.get('auto_settle_note','')}")
    return '\n'.join(lines)


def send_email(subject, body):
    if not all([MAIL_TO, MAIL_FROM, SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        raise RuntimeError('Missing email SMTP secrets. Required: MAIL_TO, MAIL_FROM, SMTP_HOST, SMTP_USER, SMTP_PASSWORD')
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = MAIL_FROM
    msg['To'] = MAIL_TO
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(MAIL_FROM, [x.strip() for x in MAIL_TO.split(',') if x.strip()], msg.as_string())


def main():
    engine = load_json(ENGINE_JSON, {})
    paper = load_json(PAPER_JSON, {'bets': [], 'summary': {}})
    state = load_json(EMAIL_STATE, {})
    send, fp, reason = should_send(engine, paper, state)
    body = build_report(engine, paper)
    status = {'generated_at': now_iso(), 'send_mode': SEND_MODE, 'should_send': send, 'reason': reason, 'mail_to': MAIL_TO, 'has_smtp': bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)}
    if send:
        subject = f"Odds Paper Report — {datetime.now(timezone.utc).strftime('%Y-%m-%d')} — {reason}"
        send_email(subject, body)
        state['last_fingerprint'] = fp
        state['last_sent_at'] = now_iso()
        state['last_sent_day'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        save_json(EMAIL_STATE, state)
        status['sent'] = True
    else:
        status['sent'] = False
    EMAIL_SUMMARY.write_text('# EMAIL REPORTER V1\n\n```json\n' + json.dumps(status, ensure_ascii=False, indent=2) + '\n```\n\n## LAST REPORT PREVIEW\n\n```text\n' + body[:6000] + '\n```\n', encoding='utf-8')
    print(f"Email Reporter complete. sent={status['sent']} reason={reason}")

if __name__ == '__main__':
    main()
