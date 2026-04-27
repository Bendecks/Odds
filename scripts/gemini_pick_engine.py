import os, json, csv, re, pathlib
from datetime import datetime
import requests

BASE = pathlib.Path('.')
OCR = BASE/'data'/'ocr_log.csv'
OUT = BASE/'output'
OUT.mkdir(exist_ok=True)
API_KEY = os.getenv('GEMINI_API_KEY','')
MODEL = 'gemini-2.5-flash'

def load_latest_possible():
    rows=[]
    if not OCR.exists(): return ''
    with open(OCR, encoding='utf-8') as f:
        r=csv.DictReader(f)
        for row in r:
            if row.get('type')=='possible_bets': rows.append(row)
    return rows[-1]['text'] if rows else ''

prompt = f'''You are a conservative betting analyst. Analyze OCR extracted bookmaker odds text. Prioritize known sports, avoid esports/esoccer/virtuals. Return max 5 picks sorted best first. If poor markets, say no bets now. Return JSON only with keys: picks(list), summary. Each pick keys: rank,event,market,selection,odds,confidence,stake_kr,label,reason. OCR:\n{load_latest_possible()[:12000]}'''

result={'summary':'No OCR data','picks':[]}
if API_KEY and load_latest_possible():
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}'
    body={"contents":[{"parts":[{"text":prompt}]}]}
    try:
        res=requests.post(url,json=body,timeout=60)
        txt=res.json()['candidates'][0]['content']['parts'][0]['text']
        m=re.search(r'\{.*\}',txt,re.S)
        if m: result=json.loads(m.group(0))
        else: result={'summary':txt,'picks':[]}
    except Exception as e:
        result={'summary':f'Gemini error: {e}','picks':[]}

with open(OUT/'picks_today.json','w',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=2)

with open(OUT/'latest_report.md','w',encoding='utf-8') as f:
    f.write('# TOP PICKS NU\n\n')
    f.write(result.get('summary','')+'\n\n')
    for p in result.get('picks',[]):
        f.write(f"## {p.get('rank')}. {p.get('event')}\n")
        f.write(f"- Market: {p.get('market')}\n- Pick: {p.get('selection')}\n- Odds: {p.get('odds')}\n- Stake: {p.get('stake_kr')} kr\n- Label: {p.get('label')}\n- Confidence: {p.get('confidence')}\n- Reason: {p.get('reason')}\n\n")
print('done')
