import json, pathlib
from datetime import datetime, timezone, timedelta
import odds_api_io_bet365 as provider
import odds_api_io_reference as reference

BET365=pathlib.Path('data/bet365_observations.jsonl')
UNIBET=pathlib.Path('data/unibet_observations.jsonl')
SUMMARY=pathlib.Path('output/bet365_market_summary.json')
UNIBET_SUMMARY=pathlib.Path('output/unibet_observer.json')
STATUS=pathlib.Path('output/bet365_join_status.json')

def dump_jsonl(path,rows):
    path.parent.mkdir(exist_ok=True)
    path.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows))

def provider_event_metadata(events, prioritized):
    events = events if isinstance(events, list) else []
    prioritized_ids = {str(row.get('id')) for row in prioritized if isinstance(row, dict)}
    key_counts = {}
    sports = {}
    leagues = {}
    samples = []
    rows_with_sport = rows_with_league = prioritized_with_sport = prioritized_with_league = 0
    for row in events:
        if not isinstance(row, dict):
            continue
        for key in row:
            key_counts[key] = key_counts.get(key, 0) + 1
        sport = row.get('sport')
        league = row.get('league')
        if sport:
            rows_with_sport += 1
            sports[str(sport)] = sports.get(str(sport), 0) + 1
        if league:
            rows_with_league += 1
            leagues[str(league)] = leagues.get(str(league), 0) + 1
        if str(row.get('id')) in prioritized_ids:
            if sport:
                prioritized_with_sport += 1
            if league:
                prioritized_with_league += 1
        if len(samples) < 5:
            samples.append({
                'id': row.get('id'),
                'home': row.get('home'),
                'away': row.get('away'),
                'sport': sport,
                'league': league,
                'date': row.get('date') or row.get('startTime') or row.get('commence_time'),
                'keys': sorted(row.keys()),
            })
    return {
        'events_total': len(events),
        'prioritized_events': len(prioritized),
        'rows_with_sport': rows_with_sport,
        'rows_with_league': rows_with_league,
        'prioritized_with_sport': prioritized_with_sport,
        'prioritized_with_league': prioritized_with_league,
        'top_sports': sorted(sports.items(), key=lambda x: (-x[1], x[0]))[:20],
        'top_leagues': sorted(leagues.items(), key=lambda x: (-x[1], x[0]))[:50],
        'event_key_counts': sorted(key_counts.items(), key=lambda x: (-x[1], x[0]))[:50],
        'samples': samples,
    }

def main():
    if not provider.KEY: raise SystemExit('Missing ODDS_API_IO_KEY')
    now=datetime.now(timezone.utc); cutoff=now+timedelta(hours=provider.MAX_HOURS)
    try: events=provider.get('/events',{'sport':'football','bookmaker':'Bet365','status':'pending','limit':'500'})
    except Exception as exc:
        STATUS.parent.mkdir(exist_ok=True); STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'source':'odds-api.io','provider_unavailable':True,'errors':[{'stage':'events','reason':type(exc).__name__}]},indent=2)+'\n'); raise
    events=(events.get('data') or events.get('events') or []) if isinstance(events,dict) else events
    prioritized=[]
    for e in events:
        if not e.get('id'): continue
        start=provider.parse_start(e.get('date') or e.get('startTime') or e.get('commence_time'))
        if start and now<start<=cutoff: prioritized.append(e)
    prioritized=prioritized[:provider.MAX_ODDS_CALLS]
    metadata=provider_event_metadata(events,prioritized)
    cache,bet365,unibet,errors,attempts,successes,ba,bs,fa,fs=provider.fetch_odds(prioritized,now)
    observed=now.isoformat()
    for row in bet365+unibet: row['observed_at']=observed
    dump_jsonl(BET365,bet365); dump_jsonl(UNIBET,unibet)
    markets={}
    for row in bet365: markets[row['market']]=markets.get(row['market'],0)+1
    SUMMARY.parent.mkdir(exist_ok=True); SUMMARY.write_text(json.dumps({'generated_at':observed,'events_queried':len(prioritized),'observations':len(bet365),'unique_markets':len(markets),'top_markets':sorted(markets.items(),key=lambda x:x[1],reverse=True)[:100],'provider_event_metadata':metadata},ensure_ascii=False,indent=2)+'\n')
    UNIBET_SUMMARY.write_text(json.dumps(provider.observer_summary(unibet,now),ensure_ascii=False,indent=2)+'\n')
    STATUS.write_text(json.dumps({'generated_at':observed,'source':'odds-api.io','provider_unavailable':False,'bet365_events_available':len(events),'events_queried':len(prioritized),'provider_event_metadata':metadata,'provider_call_attempts':attempts,'provider_call_successes':successes,'multi_calls':ba,'multi_call_successes':bs,'fallback_calls':fa,'fallback_call_successes':fs,'raw_market_observations':len(bet365),'unibet_observations':len(unibet),'unique_markets':len(markets),'max_odds_calls':provider.MAX_ODDS_CALLS,'errors':errors},ensure_ascii=False,indent=2)+'\n')
    reference.main()
    print(json.dumps({'events':len(prioritized),'bet365_observations':len(bet365),'unibet_observations':len(unibet),'calls':attempts,'successes':successes},ensure_ascii=False))

if __name__=='__main__': main()
