from pathlib import Path
import json, re
from PIL import Image
import pytesseract
import pandas as pd

BASE=Path('.')
rows=[]
for folder in ['inbox/possible_bets','inbox/history']:
    p=BASE/folder
    if not p.exists():
        continue
    for f in p.glob('*.png'):
        try:
            txt=pytesseract.image_to_string(Image.open(f), lang='eng')
        except Exception as e:
            txt=f'ERROR: {e}'
        rows.append({'file':str(f),'type':folder.split('/')[-1],'chars':len(txt),'text':txt[:5000]})

out=BASE/'data'
out.mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(out/'ocr_log.csv', index=False)
print('processed', len(rows))
