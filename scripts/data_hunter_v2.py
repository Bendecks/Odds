import os, json, pathlib, requests, re, statistics
from datetime import datetime, timezone, date

BASE = pathlib.Path('.')
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)

GEMINI = os.getenv('GEMINI_API_KEY','')
ODDS = os.getenv('THE_ODDS_API_KEY','')
FD = os.getenv('FOOTBALL_DATA_API_KEY','')
MODEL = 'gemini-2.5-flash'

ALLOWED_PREFIXES = (
    'tennis_atp','tennis_wta','basketball_nba','icehockey_nhl',
    'soccer_epl','soccer_spain_la_liga','soccer_germany_bundesliga',
    'soccer_italy_serie_a','soccer_uefa_champs_league','soccer_denmark_superliga'
)

MAX_HOURS = 72
MAX_STAKE = 5

def get_json(url, headers=None, params=None):
    r = requests.get(url, headers=headers or {}, params=params or {}, timeout=45)
    r.raise_for_status()
    return r.json()


def allowed_sport(sk):
    return any(sk.startswith(p) for p in ALLOWED_PREFIXES)


def upcoming(g):
    try:
        t = datetime.fromisoformat(g.get('commence_time','').replace('Z','+00:00'))
        hrs = (t - datetime.now(timezone.utc)).total_seconds()/3600
        return 0 < hrs <= MAX_HOURS
    except:
        return False


def build_games():
    games = []
    if not ODDS:
        return games

    raw = get_json('https://api.the-odds-api.com/v4/sports/upcoming/odds',
        params={'apiKey':ODDS,'regions':'eu,uk','markets':'h2h','oddsFormat':'decimal'})

    for g in raw:
        sk = g.get('sport_key','')
        if not allowed_sport(sk) or not upcoming(g):
            continue

        books = g.get('bookmakers',[])
        if len(books) < 3:
            continue

        prices = {}
        for b in books:
            for m in b.get('markets',[]):
                if m.get('key')!='h2h': continue
                for o in m.get('outcomes',[]):
                    try:
                        p=float(o['price'])
                        prices.setdefault(o['name'],[]).append(p)
                    except:
                        continue

        selections=[]
        for name,arr in prices.items():
            if len(arr)<3 or name.lower()=='draw': continue
            best=max(arr)
            med=statistics.median(arr)
            edge=(best/med)-1 if med else 0
            selections.append({
                'team':name,
                'best_odds':round(best,2),
                'median_odds':round(med,2),
                'edge_pct':round(edge*100,1),
                'books':len(arr)
            })

        if selections:
            games.append({
                'event': f"{g.get('home_team')} vs {g.get('away_team')}",
                'sport': sk,
                'start': g.get('commence_time'),
                'selections': sorted(selections, key=lambda x:x['edge_pct'], reverse=True)[:3]
            })

    return games[:40]


def get_football_context():
    if not FD: return {}
    try:
        d=date.today().isoformat()
        return get_json('https://api.football-data.org/v4/matches',
            headers={'X-Auth-Token':FD},
            params={'dateFrom':d,'dateTo':d})
    except:
        return {}


def run_gemini(games, football):
    if not GEMINI:
        return {'summary':'Missing GEMINI','top_bets':[],'watchlist':[],'pass':[]}

    payload = {'games':games,'football':football}

    prompt = '''You are a sharp betting analyst.
Rules:
- Max stake 5 kr
- Prefer NHL, NBA, ATP/WTA, top football
- Only pick if value exists (edge + context)
- Use rest, schedule, form if possible
- If no value: return no bets
Return JSON only: summary, top_bets, watchlist, pass
Each bet: event,pick,odds,confidence,stake_kr,reason
Data:\n'''+json.dumps(payload)[:200000]

    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}'
    body={"contents":[{"parts":[{"text":prompt}]}]}

    try:
        r=requests.post(url,json=body,timeout=90)
        r.raise_for_status()
        txt=r.json()['candidates'][0]['content']['parts'][0]['text']
        m=re.search(r'\{.*\}',txt,re.S)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        return {'summary':f'error {e}','top_bets':[],'watchlist':[],'pass':[]}

    return {'summary':'no parse','top_bets':[],'watchlist':[],'pass':[]}


def main():
    games = build_games()
    football = get_football_context()
    result = run_gemini(games, football)

    (OUT/'data_hunter_v2.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

    with open(OUT/'data_hunter_v2.md','w',encoding='utf-8') as f:
        f.write('# DATA HUNTER V2\n\n'+result.get('summary','')+'\n\n')
        for sec in ['top_bets','watchlist','pass']:
            f.write('## '+sec.upper()+'\n')
            for x in result.get(sec,[]):
                f.write(f"- {x.get('event')} | {x.get('pick')} | {x.get('odds')} | stake {x.get('stake_kr')} | {x.get('reason')}\n")
            f.write('\n')

    print(result.get('summary','done'))


if __name__ == '__main__':
    main()
