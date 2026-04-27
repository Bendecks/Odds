import os, json, pathlib, datetime, requests

OUT = pathlib.Path('output')
OUT.mkdir(exist_ok=True)

results = []

def probe(name, url, headers=None, params=None):
    item = {"source": name, "ok": False, "status_code": None, "error": None, "sample": None}
    try:
        r = requests.get(url, headers=headers or {}, params=params or {}, timeout=30)
        item["status_code"] = r.status_code
        item["ok"] = 200 <= r.status_code < 300
        try:
            data = r.json()
            item["sample"] = data if isinstance(data, dict) else data[:2]
        except Exception:
            item["sample"] = r.text[:500]
    except Exception as e:
        item["error"] = str(e)
    results.append(item)

# 1) The Odds API - broad odds source
odds_key = os.getenv('THE_ODDS_API_KEY', '')
if odds_key:
    probe(
        'the_odds_api_sports',
        'https://api.the-odds-api.com/v4/sports',
        params={'apiKey': odds_key}
    )
    probe(
        'the_odds_api_upcoming_h2h_eu',
        'https://api.the-odds-api.com/v4/sports/upcoming/odds',
        params={'apiKey': odds_key, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
    )
else:
    results.append({"source":"the_odds_api","ok":False,"error":"Missing THE_ODDS_API_KEY secret"})

# 2) Odds-API.io - odds source with bet365 coverage claimed by provider
oddsio_key = os.getenv('ODDS_API_IO_KEY', '')
if oddsio_key:
    probe(
        'odds_api_io_status',
        'https://api.odds-api.io/v3/sports',
        headers={'X-Api-Key': oddsio_key}
    )
else:
    results.append({"source":"odds_api_io","ok":False,"error":"Missing ODDS_API_IO_KEY secret"})

# 3) football-data.org - fixtures/standings for top football, not odds
fd_key = os.getenv('FOOTBALL_DATA_API_KEY', '')
if fd_key:
    today = datetime.date.today().isoformat()
    probe(
        'football_data_matches_today',
        'https://api.football-data.org/v4/matches',
        headers={'X-Auth-Token': fd_key},
        params={'dateFrom': today, 'dateTo': today}
    )
else:
    results.append({"source":"football_data","ok":False,"error":"Missing FOOTBALL_DATA_API_KEY secret"})

# 4) balldontlie - NBA stats/odds/injuries depending on account access
bdl_key = os.getenv('BALLDONTLIE_API_KEY', '')
if bdl_key:
    probe(
        'balldontlie_nba_games_today',
        'https://api.balldontlie.io/v1/games',
        headers={'Authorization': bdl_key},
        params={'dates[]': datetime.date.today().isoformat(), 'per_page': 5}
    )
else:
    results.append({"source":"balldontlie","ok":False,"error":"Missing BALLDONTLIE_API_KEY secret"})

with open(OUT/'source_probe.json','w',encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

with open(OUT/'source_probe.md','w',encoding='utf-8') as f:
    f.write('# DATA SOURCE PROBE\n\n')
    for item in results:
        status = '✅ OK' if item.get('ok') else '❌ FEJL/MANGLER'
        f.write(f"## {item.get('source')} — {status}\n")
        f.write(f"- status_code: {item.get('status_code')}\n")
        if item.get('error'):
            f.write(f"- error: {item.get('error')}\n")
        sample = json.dumps(item.get('sample'), ensure_ascii=False)[:1200]
        if sample and sample != 'null':
            f.write(f"- sample: `{sample}`\n")
        f.write('\n')

print(json.dumps(results, ensure_ascii=False, indent=2))
