import json, pathlib

SRC=pathlib.Path('output/the_odds_feed_status.json'); OUT=pathlib.Path('output/quota_status.json')

def main():
    try:s=json.loads(SRC.read_text())
    except Exception:s={}
    q=s.get('quota') or {}; remaining=q.get('remaining')
    try:r=int(remaining)
    except Exception:r=None
    status={'remaining':r,'used':q.get('used'),'last':q.get('last'),'low_quota':r is not None and r<50,'critical_quota':r is not None and r<20}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(status))
if __name__=='__main__':main()
