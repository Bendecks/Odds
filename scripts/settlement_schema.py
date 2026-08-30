import hashlib, json

DECISIVE={'win','loss'}
TERMINAL={'win','loss','push','void'}

def signal_key(x):
    return '|'.join(str(x.get(k,'')) for k in ('event','market','pick','price_timestamp','model_version'))

def settlement_key(x):
    return str(x.get('signal_key') or signal_key(x))

def normalize_result(v): return str(v or '').strip().lower()

def valid_settlement(x):
    result=normalize_result(x.get('result'))
    return bool(settlement_key(x)) and result in TERMINAL

def profit_dkk(x):
    result=normalize_result(x.get('result'))
    try: stake=float(x.get('stake_dkk') if x.get('stake_dkk') is not None else x.get('stake',0))
    except Exception: return None
    if result=='win':
        try: return round(stake*(float(x.get('odds'))-1),2)
        except Exception: return None
    if result=='loss': return round(-stake,2)
    if result in ('push','void'): return 0.0
    return None

def clv_pct(x):
    try:
        taken=float(x.get('odds')); close=float(x.get('closing_odds'))
        if taken<=1 or close<=1:return None
        return round((taken/close-1)*100,4)
    except Exception:return None

def fingerprint(x):
    raw=json.dumps({k:x.get(k) for k in ('signal_key','result','odds','closing_odds','settled_at')},sort_keys=True,separators=(',',':'))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
