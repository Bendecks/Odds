import os, json, pathlib, requests, re, unicodedata
from datetime import datetime, timezone, timedelta

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)
PAPER_JSON = OUT / 'paper_bets.json'
AUTO_MD = OUT / 'paper_auto_settler_summary.md'
RESULTS_JSON = OUT / 'paper_auto_results.json'

FOOTBALL_DATA_API_KEY = os.getenv('FOOTBALL_DATA_API_KEY', '')
FOOTBALL_DATA_COMPETITIONS = [x.strip() for x in os.getenv('FOOTBALL_DATA_COMPETITIONS', 'PL,PD,BL1,SA,FL1,DED,PPL,CL').split(',') if x.strip()]
SOCCER_END_HOURS = float(os.getenv('SOCCER_END_HOURS', '2.7'))


def now_iso(): return datetime.now(timezone.utc).isoformat()
def now_dt(): return datetime.now(timezone.utc)

def load_json(path, default):
    try:
        if path.exists(): return json.loads(path.read_text(encoding='utf-8'))
    except Exception: pass
    return default

def save_json(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def parse_dt(v):
    try: return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except Exception: return None

def norm(s):
    s = str(s or '').lower()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.replace('koeln', 'koln')
    s = re.sub(r'\b(football|club|fc|cf|sc|sv|afc|bc|team|1)\b', '', s)
    s = re.sub(r'[^a-z0-9]+', '', s)
    return s

def team_match(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb: return False
    return na == nb or (len(na) >= 5 and len(nb) >= 5 and (na in nb or nb in na))

def split_event(event):
    parts = str(event or '').split(' vs ')
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (None, None)

def is_soccer(bet):
    return str(bet.get('sport') or '').startswith('soccer_') or bet.get('sport_bucket') == 'soccer'

def likely_finished(bet):
    start = parse_dt(bet.get('start'))
    return bool(start and now_dt() >= start + timedelta(hours=SOCCER_END_HOURS))

def date_window(open_bets):
    dates = []
    for b in open_bets:
        if not is_soccer(b): continue
        d = parse_dt(b.get('start'))
        if d: dates.append(d.date())
    if not dates: return None, None
    return (min(dates) - timedelta(days=1)).isoformat(), (max(dates) + timedelta(days=1)).isoformat()

def fd_call(params):
    if not FOOTBALL_DATA_API_KEY: return {}
    try:
        r = requests.get('https://api.football-data.org/v4/matches', params=params, headers={'X-Auth-Token': FOOTBALL_DATA_API_KEY}, timeout=45)
        if not r.ok: return {'_error': f'{r.status_code} {r.text[:300]}'}
        return r.json()
    except Exception as e:
        return {'_error': str(e)[:300]}

def get_football_data_matches(open_bets):
    date_from, date_to = date_window(open_bets)
    if not date_from: return [], []
    out, errors = [], []
    for comp in FOOTBALL_DATA_COMPETITIONS:
        data = fd_call({'dateFrom': date_from, 'dateTo': date_to, 'competitions': comp})
        if data.get('_error'):
            errors.append(f'{comp}: {data.get("_error")}')
            continue
        for m in data.get('matches', []) if isinstance(data, dict) else []:
            home = (m.get('homeTeam') or {}).get('name')
            away = (m.get('awayTeam') or {}).get('name')
            ft = ((m.get('score') or {}).get('fullTime') or {})
            out.append({
                'source': 'football-data', 'competition': comp, 'id': m.get('id'),
                'home_team': home, 'away_team': away, 'commence_time': m.get('utcDate'),
                'status': m.get('status'), 'scores': {'home': ft.get('home'), 'away': ft.get('away')}
            })
    return out, errors

def score_map(game):
    home, away = game.get('home_team'), game.get('away_team')
    scores = game.get('scores') or {}
    out = {}
    try:
        if home and scores.get('home') is not None: out[norm(home)] = float(scores.get('home'))
        if away and scores.get('away') is not None: out[norm(away)] = float(scores.get('away'))
    except Exception: pass
    return out

def game_completed(game, bet):
    status = str(game.get('status') or '').lower()
    if status in ('finished','finished_provisional','ft','completed','complete','final'): return True
    return bool(score_map(game)) and likely_finished(bet)

def match_game(bet, games):
    a, b = split_event(bet.get('event'))
    if not a or not b: return None, 'bad_event_name'
    bet_start = parse_dt(bet.get('start'))
    best, best_score = None, -1
    for g in games:
        gh, ga = g.get('home_team'), g.get('away_team')
        if not gh or not ga: continue
        if not ((team_match(a, gh) and team_match(b, ga)) or (team_match(a, ga) and team_match(b, gh))): continue
        gs = parse_dt(g.get('commence_time'))
        score = 100
        if bet_start and gs:
            diff_h = abs((bet_start - gs).total_seconds()) / 3600
            if diff_h > 36: continue
            score -= diff_h
        if not game_completed(g, bet): return None, 'matched_but_not_completed_yet'
        if score > best_score:
            best, best_score = g, score
    return (best, 'matched') if best else (None, 'no_matching_football_data_match')

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
    team_a, team_b, s1, s2 = vals
    market = str(bet.get('market') or '').lower()
    pick = str(bet.get('pick') or '')
    if market != 'h2h': return None, 'unsupported_market_after_strict_mode'
    if s1 == s2: return 'push', f'{team_a} {s1:g} - {s2:g} {team_b}'
    winner = team_a if s1 > s2 else team_b
    return ('win' if team_match(pick, winner) else 'loss'), f'{team_a} {s1:g} - {s2:g} {team_b}; winner={winner}'

def calc_profit(result, stake, odds):
    try: stake, odds = float(stake or 0), float(odds or 0)
    except Exception: return 0.0
    if result == 'win': return round((odds - 1.0) * stake, 2)
    if result == 'loss': return round(-stake, 2)
    return 0.0

def summarize(bets):
    open_bets = [b for b in bets if b.get('status') == 'open']
    settled = [b for b in bets if b.get('status') == 'settled']
    won = [b for b in settled if b.get('result') == 'win']
    lost = [b for b in settled if b.get('result') == 'loss']
    push = [b for b in settled if b.get('result') in ('push','void')]
    stake = sum(float(b.get('paper_stake') or 0) for b in settled if b.get('result') in ('win','loss'))
    profit = sum(float(b.get('profit') or 0) for b in settled)
    return {'open_count': len(open_bets), 'settled_count': len(settled), 'won': len(won), 'lost': len(lost), 'push_void': len(push), 'settled_stake': round(stake,2), 'profit': round(profit,2), 'roi_pct': round((profit/stake*100) if stake else 0, 2), 'hitrate_pct': round((len(won)/(len(won)+len(lost))*100) if (len(won)+len(lost)) else 0, 2)}

def write_md(bets, applied, checked, pending, unmatched, diagnostics, fd_count, fd_errors):
    with AUTO_MD.open('w', encoding='utf-8') as f:
        f.write('# PAPER AUTO SETTLER — FOOTBALL-DATA STRICT\n\n')
        f.write(f'Generated: {now_iso()}\n\n')
        f.write(f'Checked open bets: {checked} | Auto-settled: {applied} | Pending/not finished: {pending} | Unmatched: {unmatched}\n\n')
        f.write(f'football-data matches loaded: {fd_count}\n\n')
        if fd_errors:
            f.write('## FOOTBALL-DATA ERRORS\n')
            for e in fd_errors[:30]: f.write(f'- {e}\n')
            f.write('\n')
        f.write('## SUMMARY\n```json\n' + json.dumps(summarize(bets), ensure_ascii=False, indent=2) + '\n```\n\n')
        f.write('## DIAGNOSTICS\n')
        for d in diagnostics[-250:]: f.write(f"- {d.get('id')} | {d.get('event')} | {d.get('status')} | {d.get('note')}\n")

def main():
    paper = load_json(PAPER_JSON, {'bets': []})
    bets = paper.get('bets') if isinstance(paper.get('bets'), list) else []
    open_bets = [b for b in bets if b.get('status') == 'open']
    fd_matches, fd_errors = get_football_data_matches(open_bets)
    applied = checked = pending = unmatched = 0
    diagnostics, results = [], []
    for b in open_bets:
        checked += 1
        if not is_soccer(b):
            unmatched += 1; diagnostics.append({'id': b.get('id'), 'event': b.get('event'), 'status': 'unmatched', 'note': 'non_soccer_open_bet'}); continue
        if not likely_finished(b):
            pending += 1; diagnostics.append({'id': b.get('id'), 'event': b.get('event'), 'status': 'pending', 'note': 'kampen forventes ikke færdig endnu'}); continue
        game, note = match_game(b, fd_matches)
        if not game:
            if note == 'matched_but_not_completed_yet': pending += 1
            else: unmatched += 1
            diagnostics.append({'id': b.get('id'), 'event': b.get('event'), 'status': 'pending' if note == 'matched_but_not_completed_yet' else 'unmatched', 'note': note}); continue
        result, settle_note = settle_bet(b, game)
        if result not in ('win','loss','push'):
            unmatched += 1; diagnostics.append({'id': b.get('id'), 'event': b.get('event'), 'status': 'unmatched', 'note': settle_note}); continue
        b['status'] = 'settled'; b['result'] = result; b['settled_at'] = now_iso(); b['profit'] = calc_profit(result, b.get('paper_stake'), b.get('odds'))
        b['auto_settled'] = True; b['auto_settle_note'] = settle_note; b['result_source'] = 'football-data'
        applied += 1
        diagnostics.append({'id': b.get('id'), 'event': b.get('event'), 'status': 'settled', 'note': settle_note})
        results.append({'id': b.get('id'), 'result': result, 'profit': b.get('profit'), 'note': settle_note, 'source': 'football-data'})
    paper['updated_at'] = now_iso(); paper['bets'] = bets; paper['summary'] = summarize(bets)
    save_json(PAPER_JSON, paper)
    save_json(RESULTS_JSON, {'generated_at': now_iso(), 'results': results, 'diagnostics': diagnostics, 'football_data_matches_loaded': len(fd_matches), 'football_data_errors': fd_errors})
    write_md(bets, applied, checked, pending, unmatched, diagnostics, len(fd_matches), fd_errors)
    print(f'Paper Auto Settler complete. checked={checked} applied={applied} pending={pending} unmatched={unmatched} football_data={len(fd_matches)}')

if __name__ == '__main__': main()
