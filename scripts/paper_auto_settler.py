import os, json, pathlib, requests, re, unicodedata
from datetime import datetime, timezone, timedelta

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
PAPER_JSON = OUT / 'paper_bets.json'
AUTO_MD = OUT / 'paper_auto_settler_summary.md'
RESULTS_JSON = OUT / 'paper_auto_results.json'

THE_ODDS_API_KEY = os.getenv('THE_ODDS_API_KEY','')
ODDS_API_IO_KEY = os.getenv('ODDS_API_IO_KEY','')
DAYS_FROM = int(os.getenv('SCORES_DAYS_FROM','3'))
ODDS_IO_BASE = 'https://api.odds-api.io/v3'

SPORTS = [
    'soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga',
    'basketball_nba','icehockey_nhl','baseball_mlb','americanfootball_nfl','mma_mixed_martial_arts'
]

SPORT_END_HOURS = {
    'soccer': 2.4,
    'basketball': 3.2,
    'icehockey': 3.2,
    'baseball': 4.5,
    'americanfootball': 4.2,
    'mma': 7.0,
    'other': 4.0,
}

ODDS_IO_LEAGUE_HINTS = {
    'soccer_epl': ['england-premier-league'],
    'soccer_spain_la_liga': ['spain-laliga'],
    'soccer_germany_bundesliga': ['germany-bundesliga'],
    'icehockey_nhl': ['usa-nhl'],
    'basketball_nba': ['usa-nba'],
}


def now_iso(): return datetime.now(timezone.utc).isoformat()
def now_dt(): return datetime.now(timezone.utc)

def load_json(path, default):
    try:
        if path.exists(): return json.loads(path.read_text(encoding='utf-8'))
    except Exception: pass
    return default

def save_json(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def norm(s):
    s = str(s or '').lower()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.replace('koln','koln').replace('koeln','koln')
    s = re.sub(r'\b(fc|cf|sc|sv|afc|bc|club|team|1)\b', '', s)
    s = re.sub(r'[^a-z0-9]+', '', s)
    return s

def team_match(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb: return False
    if na == nb: return True
    if len(na) >= 5 and len(nb) >= 5 and (na in nb or nb in na): return True
    return False

def parse_dt(v):
    try: return datetime.fromisoformat(str(v).replace('Z','+00:00'))
    except Exception: return None

def split_event(event):
    parts = str(event or '').split(' vs ')
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (None, None)

def sport_bucket(s):
    s = str(s or '').lower()
    if s.startswith('soccer_'): return 'soccer'
    if s.startswith('basketball_'): return 'basketball'
    if s.startswith('icehockey_'): return 'icehockey'
    if s.startswith('baseball_'): return 'baseball'
    if s.startswith('americanfootball_'): return 'americanfootball'
    if s.startswith('mma_'): return 'mma'
    return 'other'

def likely_finished(bet):
    start = parse_dt(bet.get('start'))
    if not start: return False
    hours = SPORT_END_HOURS.get(sport_bucket(bet.get('sport')), SPORT_END_HOURS['other'])
    return now_dt() >= start + timedelta(hours=hours)

def get_scores(sport):
    if not THE_ODDS_API_KEY: return []
    url = f'https://api.the-odds-api.com/v4/sports/{sport}/scores/'
    try:
        r = requests.get(url, params={'apiKey': THE_ODDS_API_KEY, 'daysFrom': DAYS_FROM, 'dateFormat': 'iso'}, timeout=60)
        if not r.ok: return []
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception: return []

def odds_io_call(path, params):
    if not ODDS_API_IO_KEY: return []
    p = dict(params or {})
    p['apiKey'] = ODDS_API_IO_KEY
    try:
        r = requests.get(ODDS_IO_BASE + path, params=p, timeout=60)
        if not r.ok: return []
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception: return []

def odds_io_sport_for_bet(bet):
    s = str(bet.get('sport') or '')
    if s.startswith('soccer_'): return 'football'
    if s.startswith('basketball_'): return 'basketball'
    if s.startswith('icehockey_'): return 'ice-hockey'
    if s.startswith('tennis_'): return 'tennis'
    return None

def odds_io_leagues_for_bet(bet):
    sport = odds_io_sport_for_bet(bet)
    if not sport: return []
    hints = ODDS_IO_LEAGUE_HINTS.get(str(bet.get('sport') or ''), [])
    if hints: return hints
    leagues = odds_io_call('/leagues', {'sport': sport})
    rows = [x for x in leagues if isinstance(x, dict) and x.get('slug') and int(x.get('eventsCount') or 0) > 0]
    rows = sorted(rows, key=lambda x: int(x.get('eventsCount') or 0), reverse=True)
    return [x.get('slug') for x in rows[:3]]

def get_odds_io_events_for_open_bets(open_bets):
    # Fetch only relevant league event lists, then match locally.
    out = []
    fetched = set()
    for b in open_bets:
        sport = odds_io_sport_for_bet(b)
        if not sport: continue
        for league in odds_io_leagues_for_bet(b):
            key = (sport, league)
            if key in fetched: continue
            fetched.add(key)
            events = odds_io_call('/events', {'sport': sport, 'league': league})
            for ev in events:
                if not isinstance(ev, dict): continue
                out.append({
                    'source': 'odds-api.io',
                    'id': ev.get('id'),
                    'home_team': ev.get('home'),
                    'away_team': ev.get('away'),
                    'commence_time': ev.get('date'),
                    'status': ev.get('status'),
                    'scores': ev.get('scores'),
                    'league': (ev.get('league') or {}).get('slug') if isinstance(ev.get('league'), dict) else None,
                    'sport_key': sport,
                })
    return out

def candidate_sports_for_bet(bet):
    s = str(bet.get('sport') or '')
    if s in SPORTS: return [s]
    if s.startswith('soccer_'): return [x for x in SPORTS if x.startswith('soccer_')]
    if s.startswith('basketball_'): return ['basketball_nba']
    if s.startswith('icehockey_'): return ['icehockey_nhl']
    if s.startswith('baseball_'): return ['baseball_mlb']
    if s.startswith('americanfootball_'): return ['americanfootball_nfl']
    if s.startswith('mma_'): return ['mma_mixed_martial_arts']
    return SPORTS

def score_map(game):
    scores = game.get('scores')
    out = {}
    if isinstance(scores, list):
        for row in scores:
            if isinstance(row, dict):
                try: out[norm(row.get('name'))] = float(row.get('score'))
                except Exception: pass
    elif isinstance(scores, dict):
        try:
            home = game.get('home_team') or game.get('home')
            away = game.get('away_team') or game.get('away')
            if home is not None and scores.get('home') is not None: out[norm(home)] = float(scores.get('home'))
            if away is not None and scores.get('away') is not None: out[norm(away)] = float(scores.get('away'))
        except Exception: pass
    return out

def game_completed(game, bet):
    status = str(game.get('status') or '').lower()
    if game.get('completed') is True: return True
    if status in ('completed','complete','finished','ended','closed','final','ft','ended_normally'): return True
    return bool(score_map(game)) and likely_finished(bet)

def match_game(bet, games):
    a, b = split_event(bet.get('event'))
    if not a or not b: return None, 'bad_event_name'
    bet_start = parse_dt(bet.get('start'))
    best, best_score = None, -1
    for g in games:
        if not isinstance(g, dict): continue
        gh = g.get('home_team') or g.get('home')
        ga = g.get('away_team') or g.get('away')
        if not gh or not ga: continue
        direct = team_match(a, gh) and team_match(b, ga)
        reverse = team_match(a, ga) and team_match(b, gh)
        if not (direct or reverse): continue
        gs = parse_dt(g.get('commence_time') or g.get('date'))
        score = 100
        if bet_start and gs:
            diff_h = abs((bet_start - gs).total_seconds()) / 3600
            if diff_h > 24: continue
            score -= diff_h
        if not game_completed(g, bet): return None, 'matched_but_not_completed_yet'
        if score > best_score:
            best_score, best = score, g
    return (best, 'matched') if best else (None, 'no_matching_score_game')

def get_team_scores_for_bet(bet, game):
    a, b = split_event(bet.get('event'))
    scores = score_map(game)
    if not a or not b or not scores: return None
    sa = sb = None
    for k, v in scores.items():
        if team_match(a, k): sa = v
        if team_match(b, k): sb = v
    return (a, b, sa, sb) if sa is not None and sb is not None else None

def settle_bet(bet, game):
    vals = get_team_scores_for_bet(bet, game)
    if not vals: return None, 'score_not_found'
    homeish, awayish, s1, s2 = vals
    market = str(bet.get('market') or '').lower()
    pick = str(bet.get('pick') or '')
    point = bet.get('point')
    if market == 'h2h':
        if s1 == s2: return 'push', f'{homeish} {s1:g} - {s2:g} {awayish}'
        winner = homeish if s1 > s2 else awayish
        return ('win' if team_match(pick, winner) else 'loss'), f'{homeish} {s1:g} - {s2:g} {awayish}; winner={winner}'
    if market == 'totals':
        try: p = float(point)
        except Exception: return None, 'missing_total_point'
        total = s1 + s2
        if abs(total - p) < 1e-9: return 'push', f'total={total:g}, line={p:g}'
        want_over = norm(pick) == 'over'
        won = total > p if want_over else total < p
        return ('win' if won else 'loss'), f'{homeish} {s1:g} - {s2:g} {awayish}; total={total:g}, line={p:g}'
    if market == 'spreads':
        try: p = float(point)
        except Exception: return None, 'missing_spread_point'
        if team_match(pick, homeish): adjusted, other = s1 + p, s2
        elif team_match(pick, awayish): adjusted, other = s2 + p, s1
        else: return None, 'spread_pick_team_not_found'
        if abs(adjusted - other) < 1e-9: return 'push', f'adjusted={adjusted:g}, other={other:g}, line={p:g}'
        return ('win' if adjusted > other else 'loss'), f'{homeish} {s1:g} - {s2:g} {awayish}; adjusted={adjusted:g}, line={p:g}'
    return None, 'unsupported_market'

def calc_profit(result, stake, odds):
    try: stake, odds = float(stake or 0), float(odds or 0)
    except Exception: return 0.0
    if result == 'win': return round((odds - 1.0) * stake, 2)
    if result == 'loss': return round(-stake, 2)
    return 0.0

def summarize(bets):
    open_bets=[b for b in bets if b.get('status')=='open']
    settled=[b for b in bets if b.get('status')=='settled']
    won=[b for b in settled if b.get('result')=='win']; lost=[b for b in settled if b.get('result')=='loss']
    push=[b for b in settled if b.get('result') in ('push','void')]
    settled_stake=sum(float(b.get('paper_stake') or 0) for b in settled if b.get('result') in ('win','loss'))
    profit=sum(float(b.get('profit') or 0) for b in settled)
    roi=(profit/settled_stake*100) if settled_stake else 0
    hit=(len(won)/(len(won)+len(lost))*100) if (len(won)+len(lost)) else 0
    return {'open_count':len(open_bets),'settled_count':len(settled),'won':len(won),'lost':len(lost),'push_void':len(push),'settled_stake':round(settled_stake,2),'profit':round(profit,2),'roi_pct':round(roi,2),'hitrate_pct':round(hit,2)}

def write_md(bets, applied, checked, pending, unmatched, source_sports, diagnostics, odds_io_count):
    with AUTO_MD.open('w', encoding='utf-8') as f:
        f.write('# PAPER AUTO SETTLER V3 — MULTI SOURCE\n\n')
        f.write(f'Generated: {now_iso()}\n\n')
        f.write(f'Checked open bets: {checked} | Auto-settled: {applied} | Pending/not finished: {pending} | Unmatched: {unmatched}\n\n')
        f.write(f'The Odds API sports queried: {", ".join(source_sports)}\n\n')
        f.write(f'odds-api.io fallback events loaded: {odds_io_count}\n\n')
        f.write('## SUMMARY\n```json\n'+json.dumps(summarize(bets),ensure_ascii=False,indent=2)+'\n```\n\n')
        f.write('## DIAGNOSTICS\n')
        for d in diagnostics[-160:]: f.write(f"- {d.get('id')} | {d.get('event')} | {d.get('status')} | {d.get('source')} | {d.get('note')}\n")
        f.write('\n## RECENT SETTLED\n')
        for b in [x for x in bets if x.get('status')=='settled'][-80:]:
            f.write(f"- {b.get('id')} | {b.get('result')} | profit {b.get('profit')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} @ {b.get('odds')} | {b.get('auto_settle_note','')} | {b.get('result_source')}\n")
        f.write('\n## OPEN\n')
        for b in [x for x in bets if x.get('status')=='open'][-100:]:
            f.write(f"- {b.get('id')} | {b.get('start_local') or b.get('start')} | {b.get('sport')} | {b.get('event')} | {b.get('market')} | {b.get('pick')} {b.get('point')} @ {b.get('odds')}\n")

def main():
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    open_bets = [b for b in bets if b.get('status') == 'open']
    needed = []
    for b in open_bets:
        for s in candidate_sports_for_bet(b):
            if s not in needed: needed.append(s)
    scores_by_sport = {s: get_scores(s) for s in needed}
    odds_io_events = get_odds_io_events_for_open_bets(open_bets)
    auto_results=[]; applied=0; checked=0; unmatched=0; pending=0; diagnostics=[]
    for b in open_bets:
        checked += 1
        if not likely_finished(b):
            pending += 1; diagnostics.append({'id':b.get('id'),'event':b.get('event'),'status':'pending','source':'time','note':'kampen forventes ikke færdig endnu'}); continue
        matched = None; match_note = 'not_checked'; source = 'the-odds-api'
        for s in candidate_sports_for_bet(b):
            matched, match_note = match_game(b, scores_by_sport.get(s, []))
            if matched: break
            if match_note == 'matched_but_not_completed_yet': break
        if not matched and match_note != 'matched_but_not_completed_yet':
            matched, match_note = match_game(b, odds_io_events)
            source = 'odds-api.io'
        if not matched:
            if match_note == 'matched_but_not_completed_yet':
                pending += 1; diagnostics.append({'id':b.get('id'),'event':b.get('event'),'status':'pending','source':source,'note':match_note})
            else:
                unmatched += 1; diagnostics.append({'id':b.get('id'),'event':b.get('event'),'status':'unmatched','source':source,'note':match_note})
            continue
        result, note = settle_bet(b, matched)
        if result not in ('win','loss','push','void'):
            unmatched += 1; diagnostics.append({'id':b.get('id'),'event':b.get('event'),'status':'unmatched','source':source,'note':note}); continue
        b['status']='settled'; b['result']=result; b['settled_at']=now_iso(); b['profit']=calc_profit(result,b.get('paper_stake'),b.get('odds'))
        b['auto_settled']=True; b['auto_settle_note']=note; b['result_source']=source
        auto_results.append({'id':b.get('id'),'result':result,'profit':b.get('profit'),'note':note,'settled_at':b.get('settled_at'),'source':source})
        diagnostics.append({'id':b.get('id'),'event':b.get('event'),'status':'settled','source':source,'note':note})
        applied += 1
    paper['updated_at']=now_iso(); paper['bets']=bets; paper['summary']=summarize(bets)
    save_json(PAPER_JSON, paper)
    save_json(RESULTS_JSON, {'generated_at':now_iso(),'results':auto_results,'diagnostics':diagnostics,'odds_io_events_loaded':len(odds_io_events)})
    write_md(bets, applied, checked, pending, unmatched, needed, diagnostics, len(odds_io_events))
    print(f'Paper Auto Settler V3 complete. checked={checked} applied={applied} pending={pending} unmatched={unmatched} odds_io_events={len(odds_io_events)}')

if __name__ == '__main__': main()
