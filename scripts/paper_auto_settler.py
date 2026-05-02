import os, json, pathlib, requests, re
from datetime import datetime, timezone, timedelta

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
PAPER_JSON = OUT / 'paper_bets.json'
AUTO_MD = OUT / 'paper_auto_settler_summary.md'
RESULTS_JSON = OUT / 'paper_auto_results.json'
THE_ODDS_API_KEY = os.getenv('THE_ODDS_API_KEY','')
DAYS_FROM = int(os.getenv('SCORES_DAYS_FROM','3'))

SPORTS = [
    'soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga',
    'basketball_nba','icehockey_nhl','baseball_mlb','americanfootball_nfl','mma_mixed_martial_arts'
]


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


def norm(s):
    s = str(s or '').lower()
    s = re.sub(r'[^a-z0-9]+', '', s)
    return s


def parse_dt(v):
    try:
        return datetime.fromisoformat(str(v).replace('Z','+00:00'))
    except Exception:
        return None


def split_event(event):
    parts = str(event or '').split(' vs ')
    if len(parts) != 2:
        return None, None
    return parts[0].strip(), parts[1].strip()


def get_scores(sport):
    if not THE_ODDS_API_KEY:
        return []
    url = f'https://api.the-odds-api.com/v4/sports/{sport}/scores/'
    try:
        r = requests.get(url, params={'apiKey': THE_ODDS_API_KEY, 'daysFrom': DAYS_FROM, 'dateFormat': 'iso'}, timeout=60)
        if not r.ok:
            return []
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def candidate_sports_for_bet(bet):
    s = str(bet.get('sport') or '')
    if s in SPORTS:
        return [s]
    if s.startswith('soccer_'):
        return [x for x in SPORTS if x.startswith('soccer_')]
    if s.startswith('basketball_'):
        return ['basketball_nba']
    if s.startswith('icehockey_'):
        return ['icehockey_nhl']
    if s.startswith('baseball_'):
        return ['baseball_mlb']
    if s.startswith('americanfootball_'):
        return ['americanfootball_nfl']
    if s.startswith('mma_'):
        return ['mma_mixed_martial_arts']
    return SPORTS


def score_map(game):
    scores = game.get('scores') or []
    out = {}
    for row in scores:
        if not isinstance(row, dict):
            continue
        try:
            out[norm(row.get('name'))] = float(row.get('score'))
        except Exception:
            pass
    return out


def game_completed(game):
    if game.get('completed') is True:
        return True
    # Some APIs only populate scores/live state. Require explicit completed for auto-settle.
    return False


def match_game(bet, games):
    a, b = split_event(bet.get('event'))
    if not a or not b:
        return None
    na, nb = norm(a), norm(b)
    bet_start = parse_dt(bet.get('start'))
    best = None
    best_score = -1
    for g in games:
        if not isinstance(g, dict) or not game_completed(g):
            continue
        gh, ga = norm(g.get('home_team')), norm(g.get('away_team'))
        if not gh or not ga:
            continue
        team_match = (na == gh and nb == ga) or (na == ga and nb == gh)
        if not team_match:
            continue
        score = 100
        gs = parse_dt(g.get('commence_time'))
        if bet_start and gs:
            diff_h = abs((bet_start - gs).total_seconds()) / 3600
            if diff_h > 8:
                continue
            score -= diff_h
        if score > best_score:
            best_score = score
            best = g
    return best


def get_team_scores_for_bet(bet, game):
    a, b = split_event(bet.get('event'))
    scores = score_map(game)
    if not a or not b or not scores:
        return None
    sa = scores.get(norm(a))
    sb = scores.get(norm(b))
    if sa is None or sb is None:
        return None
    return a, b, sa, sb


def settle_bet(bet, game):
    vals = get_team_scores_for_bet(bet, game)
    if not vals:
        return None, 'score_not_found'
    homeish, awayish, s1, s2 = vals
    market = str(bet.get('market') or '').lower()
    pick = str(bet.get('pick') or '')
    point = bet.get('point')
    if market == 'h2h':
        if s1 == s2:
            return 'push', f'{homeish} {s1} - {s2} {awayish}'
        winner = homeish if s1 > s2 else awayish
        return ('win' if norm(pick) == norm(winner) else 'loss'), f'{homeish} {s1} - {s2} {awayish}; winner={winner}'
    if market == 'totals':
        try:
            p = float(point)
        except Exception:
            return None, 'missing_total_point'
        total = s1 + s2
        if abs(total - p) < 1e-9:
            return 'push', f'total={total}, line={p}'
        want_over = norm(pick) == 'over'
        won = total > p if want_over else total < p
        return ('win' if won else 'loss'), f'{homeish} {s1} - {s2} {awayish}; total={total}, line={p}'
    if market == 'spreads':
        try:
            p = float(point)
        except Exception:
            return None, 'missing_spread_point'
        if norm(pick) == norm(homeish):
            adjusted = s1 + p
            other = s2
        elif norm(pick) == norm(awayish):
            adjusted = s2 + p
            other = s1
        else:
            return None, 'spread_pick_team_not_found'
        if abs(adjusted - other) < 1e-9:
            return 'push', f'adjusted={adjusted}, other={other}, line={p}'
        return ('win' if adjusted > other else 'loss'), f'{homeish} {s1} - {s2} {awayish}; adjusted={adjusted}, line={p}'
    return None, 'unsupported_market'


def calc_profit(result, stake, odds):
    try:
        stake = float(stake or 0)
        odds = float(odds or 0)
    except Exception:
        return 0.0
    if result == 'win': return round((odds - 1.0) * stake, 2)
    if result == 'loss': return round(-stake, 2)
    return 0.0


def summarize(bets):
    open_bets=[b for b in bets if b.get('status')=='open']
    settled=[b for b in bets if b.get('status')=='settled']
    won=[b for b in settled if b.get('result')=='win']
    lost=[b for b in settled if b.get('result')=='loss']
    push=[b for b in settled if b.get('result') in ('push','void')]
    settled_stake=sum(float(b.get('paper_stake') or 0) for b in settled if b.get('result') in ('win','loss'))
    profit=sum(float(b.get('profit') or 0) for b in settled)
    roi=(profit/settled_stake*100) if settled_stake else 0
    hit=(len(won)/(len(won)+len(lost))*100) if (len(won)+len(lost)) else 0
    return {'open_count':len(open_bets),'settled_count':len(settled),'won':len(won),'lost':len(lost),'push_void':len(push),'settled_stake':round(settled_stake,2),'profit':round(profit,2),'roi_pct':round(roi,2),'hitrate_pct':round(hit,2)}


def write_md(bets, applied, checked, unmatched, source_sports):
    with AUTO_MD.open('w', encoding='utf-8') as f:
        f.write('# PAPER AUTO SETTLER V1\n\n')
        f.write(f'Generated: {now_iso()}\n\n')
        f.write(f'Checked open bets: {checked} | Auto-settled: {applied} | Unmatched/pending: {unmatched}\n\n')
        f.write(f'Source sports queried: {", ".join(source_sports)}\n\n')
        f.write('## SUMMARY\n```json\n'+json.dumps(summarize(bets),ensure_ascii=False,indent=2)+'\n```\n\n')
        f.write('## RECENT SETTLED\n')
        for b in [x for x in bets if x.get('status')=='settled'][-60:]:
            f.write(f"- {b.get('id')} | {b.get('result')} | profit {b.get('profit')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} @ {b.get('odds')} | {b.get('auto_settle_note','')}\n")
        f.write('\n## OPEN\n')
        for b in [x for x in bets if x.get('status')=='open'][-80:]:
            f.write(f"- {b.get('id')} | {b.get('start_local') or b.get('start')} | {b.get('sport')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} @ {b.get('odds')}\n")


def main():
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    open_bets = [b for b in bets if b.get('status') == 'open']
    needed = []
    for b in open_bets:
        for s in candidate_sports_for_bet(b):
            if s not in needed:
                needed.append(s)
    scores_by_sport = {s: get_scores(s) for s in needed}
    auto_results=[]
    applied=0; checked=0; unmatched=0
    for b in open_bets:
        checked += 1
        matched = None
        for s in candidate_sports_for_bet(b):
            matched = match_game(b, scores_by_sport.get(s, []))
            if matched:
                break
        if not matched:
            unmatched += 1
            continue
        result, note = settle_bet(b, matched)
        if result not in ('win','loss','push','void'):
            unmatched += 1
            continue
        b['status']='settled'
        b['result']=result
        b['settled_at']=now_iso()
        b['profit']=calc_profit(result,b.get('paper_stake'),b.get('odds'))
        b['auto_settled']=True
        b['auto_settle_note']=note
        b['result_source']='the-odds-api scores'
        auto_results.append({'id':b.get('id'),'result':result,'profit':b.get('profit'),'note':note,'settled_at':b.get('settled_at')})
        applied += 1
    paper['updated_at']=now_iso()
    paper['bets']=bets
    paper['summary']=summarize(bets)
    save_json(PAPER_JSON, paper)
    save_json(RESULTS_JSON, {'generated_at':now_iso(),'results':auto_results})
    write_md(bets, applied, checked, unmatched, needed)
    print(f'Paper Auto Settler complete. checked={checked} applied={applied} unmatched={unmatched}')

if __name__ == '__main__':
    main()
