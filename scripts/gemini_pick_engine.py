import os, json, csv, re, pathlib
import requests

BASE = pathlib.Path('.')
OCR = BASE / 'data' / 'ocr_log.csv'
BANKROLL = BASE / 'data' / 'bankroll.csv'
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)

API_KEY = os.getenv('GEMINI_API_KEY', '')
MODEL = 'gemini-2.5-flash'

ALLOWED_SPORTS = [
    'ATP', 'WTA', 'Challenger', 'NBA', 'NHL',
    'Premier League', 'La Liga', 'Bundesliga', 'Serie A',
    'Champions League', 'Europa League', 'Superliga', 'Liga ACB'
]

BANNED_MARKETS = [
    'Esoccer', 'Ebasketball', 'virtual', 'simulated', 'Battle', 'GG League', 'Volta'
]

def load_bankroll(default=80.0):
    if not BANKROLL.exists():
        return default
    try:
        rows = list(csv.DictReader(open(BANKROLL, encoding='utf-8')))
        if rows:
            return float(str(rows[-1].get('balance_kr', default)).replace(',', '.'))
    except Exception:
        pass
    return default

def load_latest_possible():
    rows = []
    if not OCR.exists():
        return ''
    with open(OCR, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('type') == 'possible_bets' and not row.get('text','').startswith('ERROR'):
                rows.append(row)
    return rows[-1]['text'] if rows else ''

def sanitize_result(result, bankroll):
    clean = []
    max_stake = max(1, round(bankroll * 0.05))
    normal_stake = max(1, round(bankroll * 0.025))
    for p in result.get('picks', []):
        text = ' '.join(str(p.get(k, '')) for k in ['event','market','selection','label','reason'])
        if any(b.lower() in text.lower() for b in BANNED_MARKETS):
            continue
        try:
            odds = float(str(p.get('odds')).replace(',', '.'))
        except Exception:
            continue
        if odds < 1.25:
            continue
        stake = p.get('stake_kr', normal_stake)
        try:
            stake = float(str(stake).replace(',', '.'))
        except Exception:
            stake = normal_stake
        p['stake_kr'] = int(min(max(1, stake), max_stake))
        clean.append(p)
    result['picks'] = clean[:5]
    if not result['picks']:
        result['summary'] = 'ingen spil nu — markets are too weak, too obscure, or mostly esports/virtuals.'
    return result

ocr_text = load_latest_possible()
bankroll = load_bankroll()

prompt = f'''
You are Bendix's conservative pre-match betting engine.

Bankroll: {bankroll:.2f} kr.
Risk profile: conservative growth, singles only, no parlays, no live betting.
Goal: prioritize safest/best picks at the top. Return zero picks if quality is poor.

STRICT RULES:
- Prefer ATP/WTA tennis, NBA, NHL, and top football.
- Avoid esports, esoccer, ebasketball, virtuals, simulations, youth/reserve/lower obscure leagues unless there is a clear edge.
- Do not force picks.
- Never recommend odds below 1.25.
- Stake must be conservative: normally 1-3 kr, max 5% of bankroll.
- If external research is unavailable and the market is obscure, return no pick.
- Singapore, reserve leagues, youth leagues, and unknown lower leagues require PASS unless there is strong supporting evidence in the OCR.

Return JSON only:
{{
  "summary": "short Danish summary",
  "picks": [
    {{"rank":1,"event":"...","market":"...","selection":"...","odds":1.55,"confidence":"7.5/10","stake_kr":2,"label":"SAFE|VALUE|AGGRESSIVE","reason":"short Danish reason"}}
  ]
}}

OCR text:
{ocr_text[:14000]}
'''

result = {'summary': 'No OCR data', 'picks': []}
if API_KEY and ocr_text:
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}'
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(url, json=body, timeout=90)
        res.raise_for_status()
        txt = res.json()['candidates'][0]['content']['parts'][0]['text']
        m = re.search(r'\{.*\}', txt, re.S)
        if m:
            result = json.loads(m.group(0))
        else:
            result = {'summary': txt, 'picks': []}
    except Exception as e:
        result = {'summary': f'Gemini error: {e}', 'picks': []}

result = sanitize_result(result, bankroll)

with open(OUT / 'picks_today.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

with open(OUT / 'latest_report.md', 'w', encoding='utf-8') as f:
    f.write('# TOP PICKS NU\n\n')
    f.write(result.get('summary', '') + '\n\n')
    for p in result.get('picks', []):
        f.write(f"## {p.get('rank')}. {p.get('event')}\n")
        f.write(f"- Market: {p.get('market')}\n")
        f.write(f"- Pick: {p.get('selection')}\n")
        f.write(f"- Odds: {p.get('odds')}\n")
        f.write(f"- Stake: {p.get('stake_kr')} kr\n")
        f.write(f"- Label: {p.get('label')}\n")
        f.write(f"- Confidence: {p.get('confidence')}\n")
        f.write(f"- Reason: {p.get('reason')}\n\n")
print('done')
