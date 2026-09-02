import json, os, pathlib, statistics
from datetime import datetime, timezone, timedelta
import requests

BASE='https://api.the-odds-api.com'
KEY=os.getenv('THE_ODDS_API_KEY') or os.getenv('ODDS_API_KEY','')
DEFAULT_SPORTS='soccer_denmark_superliga,soccer_epl,soccer_spain_la_liga,soccer_germany_bundesliga,soccer_italy_serie_a,soccer_france_ligue_one,soccer_netherlands_eredivisie,soccer_uefa_champs_league'
CORE_SPORTS=[x for x in DEFAULT_SPORTS.split(',') if x]
SPORTS_OVERRIDE=os.getenv('THE_ODDS_SPORTS','').strip()
MAX_SPORTS=int(os.getenv('THE_ODDS_MAX_SPORTS','24')); SPORTS_PER_RUN=max(1,int(os.getenv('THE_ODDS_SPORTS_PER_RUN','8')))
QUOTA_RESERVE=max(0,int(os.getenv('THE_ODDS_QUOTA_RESERVE','25')))
ROTATION_STATE=pathlib.Path('data/reference_sport_rotation.json')
BOOKMAKERS=[x.strip() for x in os.getenv('THE_ODDS_BOOKMAKERS','pinnacle,betfair_ex_eu,betsson,nordicbet,williamhill').split(',') if x.strip()]
MARKETS=[x.strip() for x in os.getenv('THE_ODDS_MARKETS','h2h,totals,spreads').split(',') if x.strip()]
MAX_HOURS=int(os.getenv('MAX_HOURS','72')); OUT=pathlib.Path('data/value_candidates.json'); STATUS=pathlib.Path('output/the_odds_feed_status.json')
def api_time(dt):return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def get(path,params):
 r=requests.get(BASE+path,params={**params,'apiKey':KEY},timeout=30); meta={'remaining':r.headers.get('x-requests-remaining'),'used':r.headers.get('x-requests-used'),'last':r.headers.get('x-requests-last')}; r.raise_for_status(); return r.json(),meta
def quota_remaining(meta):
 try:return int(meta.get('remaining'))
 except (TypeError,ValueError):return None
def quota_exhausted(meta):
 remaining=quota_remaining(meta);return remaining is not None and remaining<=QUOTA_RESERVE
def active_sports():
 if SPORTS_OVERRIDE:return [x.strip() for x in SPORTS_OVERRIDE.split(',') if x.strip()],'override'
 try:
  data,_=get('/v4/sports',{}); return sorted(set(str(x.get('key')) for x in data if x.get('active') and str(x.get('key','')).startswith('soccer_') and not x.get('has_outrights'))),'active-soccer-discovery'
 except Exception:return CORE_SPORTS[:MAX_SPORTS],'fallback-defaults'
def rotation_cursor():
 try:return max(0,int(json.loads(ROTATION_STATE.read_text()).get('cursor',0)))
 except Exception:return 0
def select_sports(pool):
 if SPORTS_OVERRIDE:return pool[:min(len(pool),SPORTS_PER_RUN)],0
 budget=min(len(pool),SPORTS_PER_RUN)
 if not budget:return [],0
 core=[s for s in CORE_SPORTS if s in pool]; core_slots=min(len(core),budget if len(pool)<=budget else max(1,budget//2)); stable=core[:core_slots]; rotating=[s for s in pool if s not in stable]; slots=budget-len(stable); cursor=rotation_cursor()
 if rotating and slots:selected=stable+[rotating[(cursor+i)%len(rotating)] for i in range(slots)];next_cursor=(cursor+slots)%len(rotating)
 else:selected=stable;next_cursor=cursor
 if len(selected)<budget:selected += [s for s in pool if s not in selected][:budget-len(selected)]
 return selected,next_cursor
def discover_sports():
 pool,source=active_sports();selected,next_cursor=select_sports(pool);return selected,source,pool,next_cursor
def price(o):
 try:return float(o.get('price',0) or 0)
 except Exception:return 0.0
def point(o):
 v=o.get('point')
 if v is None:return None
 try:return float(v)
 except Exception:return v
def market_bucket(k,o):
 if k=='totals':return ('total',point(o))
 if k=='spreads':
  p=point(o)
  try:return ('spread',abs(float(p)))
  except Exception:return ('spread',p)
 return ('market',None)
def candidate_line(k,o):return point(o) if k in ('totals','spreads') else None
def novig_fair(outcomes):
 valid=[o for o in outcomes if price(o)>1];inv=[1/price(o) for o in valid];total=sum(inv)
 return {str(o.get('name')):(1/price(o))/total for o in valid} if len(inv)>=2 and total>0 else {}
def fair_key(o):return (str(o.get('name')),point(o))
def novig_fair_by_key(outcomes):
 valid=[o for o in outcomes if price(o)>1];inv=[1/price(o) for o in valid];total=sum(inv)
 return {fair_key(o):(1/price(o))/total for o in valid} if len(inv)>=2 and total>0 else {}
def quality(n):return 'strong' if n>=4 else 'good' if n>=3 else 'limited' if n>=2 else 'weak'
def h2h_triplet(event,rows):
 h=[r for r in rows if r.get('market')=='h2h' and r.get('fair_probability') is not None];home=str(event.get('home_team'));away=str(event.get('away_team'));by={str(r.get('pick')):r for r in h};draw=next((r for r in h if str(r.get('pick')).lower()=='draw'),None);return by.get(home),by.get(away),draw
def derived_common(base,market):
 refs=sorted(set.intersection(*(set(r.get('reference_books') or []) for r in base)));books=len(refs)
 r=base[0];return {'event':r['event'],'event_id':r.get('event_id'),'sport':r.get('sport'),'commence_time':r.get('commence_time'),'market':market,'books':books,'reference_books':refs,'reference_quality':quality(books),'discovery_eligible':True,'bookmaker':'DERIVED_REFERENCE_MARKET','bet365_verified':False,'model_version':'market-consensus-v6-derived'}
def derived_markets(event,rows):
 hr,ar,draw=h2h_triplet(event,rows)
 if not (hr and ar and draw):return []
 ph,pa,pd=map(lambda r:float(r['fair_probability']),(hr,ar,draw));base=[hr,ar,draw];out=[];common=derived_common(base,'double_chance')
 for pick,p in [('1X',ph+pd),('12',ph+pa),('X2',pd+pa)]:out.append({**common,'pick':pick,'fair_probability':round(p,6),'reference_odds':round(1/p,3)})
 common=derived_common(base,'draw_no_bet')
 for pick,pw,pl in [(str(event.get('home_team')),ph,pa),(str(event.get('away_team')),pa,ph)]:
  decisive=pw+pl
  if decisive>0:
   q=pw/decisive;fair_odds=decisive/pw
   out.append({**common,'pick':pick,'fair_probability':round(q,6),'win_probability':round(pw,6),'loss_probability':round(pl,6),'push_probability':round(pd,6),'reference_odds':round(fair_odds,3),'market_semantics':'push_on_draw'})
 return out
def market_candidates(event):
 consensus={};offered={};books_by_pick={}
 for book in event.get('bookmakers',[]):
  bk=str(book.get('key') or book.get('title') or 'unknown')
  for market in book.get('markets',[]):
   k=str(market.get('key') or '')
   if k not in MARKETS:continue
   grouped={}
   for o in market.get('outcomes',[]):grouped.setdefault(market_bucket(k,o),[]).append(o)
   for outcomes in grouped.values():
    fair=novig_fair_by_key(outcomes)
    for o in outcomes:
     p=price(o)
     if p<=1:continue
     pick=str(o.get('name'));line=candidate_line(k,o);key=(k,pick,line);fk=fair_key(o)
     if fk in fair:consensus.setdefault(key,[]).append(fair[fk])
     offered.setdefault(key,[]).append(p);books_by_pick.setdefault(key,set()).add(bk)
 rows=[]
 for (k,pick,line),prices in offered.items():
  probs=consensus.get((k,pick,line),[]);fair=statistics.median(probs) if probs else None;n=len(books_by_pick.get((k,pick,line),set()));row={'event':f"{event.get('home_team')} vs {event.get('away_team')}",'event_id':event.get('id'),'sport':event.get('sport_key') or event.get('sport'),'commence_time':event.get('commence_time'),'market':k,'pick':pick,'reference_odds':round(max(prices),3),'fair_probability':round(fair,6) if fair is not None else None,'books':n,'reference_books':sorted(books_by_pick.get((k,pick,line),set())),'reference_quality':quality(n),'discovery_eligible':True,'bookmaker':'REFERENCE_MARKET','bet365_verified':False,'model_version':'market-consensus-v6'}
  if line is not None:row['line']=line
  rows.append(row)
 rows.extend(derived_markets(event,rows));return rows
def main():
 if not KEY:raise SystemExit('Missing THE_ODDS_API_KEY/ODDS_API_KEY')
 sports,source,pool,next_cursor=discover_sports();now=datetime.now(timezone.utc);end=now+timedelta(hours=MAX_HOURS);candidates=[];last_meta={};events_seen=0;errors=[];quota_stopped=False;requested=[];params={'bookmakers':','.join(BOOKMAKERS),'markets':','.join(MARKETS),'oddsFormat':'decimal','dateFormat':'iso','commenceTimeFrom':api_time(now),'commenceTimeTo':api_time(end)}
 for sport in sports:
  if quota_exhausted(last_meta):quota_stopped=True;break
  requested.append(sport)
  try:data,last_meta=get(f'/v4/sports/{sport}/odds',params)
  except requests.HTTPError as e:
   meta={'remaining':e.response.headers.get('x-requests-remaining'),'used':e.response.headers.get('x-requests-used'),'last':e.response.headers.get('x-requests-last')} if e.response is not None else {}
   if meta:last_meta=meta
   errors.append({'sport':sport,'status':e.response.status_code if e.response is not None else None,'error':e.response.text[:500] if e.response is not None else str(e)})
   if quota_exhausted(last_meta):quota_stopped=True;break
   continue
  events_seen+=len(data)
  for event in data:event['sport_key']=sport;candidates.extend(market_candidates(event))
 candidates.sort(key=lambda x:(x['books'],x['fair_probability'] or 0),reverse=True);quality_counts={};pick_counts={'draw':0,'team':0};market_counts={}
 for c in candidates:quality_counts[c['reference_quality']]=quality_counts.get(c['reference_quality'],0)+1;pick_counts['draw' if str(c['pick']).lower()=='draw' else 'team']+=1;market_counts[c['market']]=market_counts.get(c['market'],0)+1
 OUT.parent.mkdir(exist_ok=True);STATUS.parent.mkdir(exist_ok=True);ROTATION_STATE.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n')
 if not SPORTS_OVERRIDE:ROTATION_STATE.write_text(json.dumps({'cursor':next_cursor,'pool_size':len(pool),'last_sports':requested,'updated_at':now.isoformat()},ensure_ascii=False,indent=2)+'\n')
 STATUS.write_text(json.dumps({'generated_at':now.isoformat(),'model_version':'market-consensus-v6','sports_source':source,'active_soccer_pool_size':len(pool),'sports_requested':requested,'sports_planned':sports,'sports_count':len(requested),'sports_per_run':SPORTS_PER_RUN,'max_sports':MAX_SPORTS,'rotation_next_cursor':next_cursor,'bookmakers':BOOKMAKERS,'markets':MARKETS,'derived_markets':['double_chance','draw_no_bet'],'events_seen':events_seen,'reference_observations':len(candidates),'quality_counts':quality_counts,'market_counts':market_counts,'pick_type_counts':pick_counts,'discovery_policy':'active-soccer quota rotation with quota reserve; direct h2h/totals/spreads plus derived double-chance and push-aware draw-no-bet from 1X2 consensus','quota':last_meta,'quota_reserve':QUOTA_RESERVE,'quota_stopped':quota_stopped,'errors':errors},ensure_ascii=False,indent=2)+'\n');print(f'{len(candidates)} reference observations from {events_seen} events; quota={last_meta}; quota_stopped={quota_stopped}; errors={len(errors)}')
 if errors and events_seen==0:raise SystemExit('No events returned; see feed status')
if __name__=='__main__':main()
