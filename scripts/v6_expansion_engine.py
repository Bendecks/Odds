# SMART VOLUME PATCH
# Only modifying rank logic

# (rest of file unchanged above)

def smart_rank(cands):
    high = [c for c in cands if c['pre_score'] >= 8 and int(c.get('books') or 0) >= 2]
    mid = [c for c in cands if 7 <= c['pre_score'] < 8 and int(c.get('books') or 0) >= 2]

    if len(high) >= 3:
        top = high[:MAX_TOP_BETS]
    elif len(high) + len(mid) >= 2:
        top = (high + mid)[:MAX_TOP_BETS]
    else:
        top = (high + mid)[:2]

    watch = [c for c in cands if c not in top]

    DIAG['top_count'] = len(top)

    return {
        'summary': ('ingen spil nu' if not top else f'{len(top)} smart bets'),
        'top_bets': top,
        'watchlist': watch[:80],
        'pass': []
    }

# replace old rank call
cands = collect_candidates()
res = smart_rank(cands)
res['mode'] = 'V17_SMART_VOLUME_ENGINE'
res['generated_at'] = now_iso()
res['candidate_count'] = len(cands)
res['diagnostics'] = DIAG

(OUT / 'v6_expansion_engine.json').write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print(res['summary'])
