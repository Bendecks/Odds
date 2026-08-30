import json,pathlib,re,unicodedata
from datetime import datetime,timezone

CAND=pathlib.Path('data/value_candidates.json'); OCR=pathlib.Path('output/ocr_possible_bets_analysis.json'); STATUS=pathlib.Path('output/bet365_join_status.json')

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower(); return re.sub(r'[^a-z0-9]','',s)
def dt(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception:return None

def main():
    refs=json.loads(CAND.read_text()) if CAND.exists() else []; data=json.loads(OCR.read_text()) if OCR.exists() else {}; now=datetime.now(timezone.utc); prices=[]
    for f in data.get('files',[]):
        stamp=dt(f.get('source_capture_time_local'))
        if not stamp or abs((now-stamp).total_seconds())>1200:continue
        for c in f.get('candidates') or []:
            if str(c.get('market')).lower() not in ('1x2','h2h'):continue
            prices.append({'event':c.get('event'),'pick':c.get('selection'),'odds':c.get('odds'),'timestamp':stamp.isoformat()})
    matched=0
    for r in refs:
        for p in prices:
            if norm(r.get('event'))==norm(p.get('event')) and norm(r.get('pick'))==norm(p.get('pick')):
                r['bet365_odds']=float(p['odds']); r['bet365_timestamp']=p['timestamp']; r['bet365_verified']=True; r['bet365_source']='fresh_ocr'; matched+=1; break
    CAND.write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n'); STATUS.parent.mkdir(exist_ok=True); STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'fresh_bet365_prices':len(prices),'matched_candidates':matched},indent=2)+'\n'); print(f'fresh prices={len(prices)} matched={matched}')
if __name__=='__main__':main()
