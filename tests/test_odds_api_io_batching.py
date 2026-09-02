import importlib.util,pathlib,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bet365',ROOT/'scripts'/'odds_api_io_bet365.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def event(i):return {'id':i,'home':f'H{i}','away':f'A{i}','date':'2026-09-01T12:00:00Z'}
def odds(i):return {'id':i,'bookmakers':{'Bet365':[{'name':'ML','updatedAt':'2026-08-31T06:00:00Z','odds':[{'home':'2.0','draw':'3.0','away':'4.0'}]}]}}
def odds_both(i):
 d=odds(i);d['bookmakers']['Unibet']=[{'name':'ML','updatedAt':'2026-08-31T06:00:00Z','odds':[{'home':'2.1','draw':'3.1','away':'3.9'}]}];return d
class BatchTests(unittest.TestCase):
 def test_chunks_max_ten(self):
  self.assertEqual([len(x) for x in m.chunks(list(range(23)),10)],[10,10,3])
 def test_batch_replaces_per_event_calls(self):
  events=[event(i) for i in range(1,13)]
  def fake(path,params):
   self.assertEqual(path,'/odds/multi');self.assertEqual(params['bookmakers'],'Bet365,Unibet');return [odds(int(x)) for x in params['eventIds'].split(',')]
  with patch.object(m,'get',side_effect=fake):
   cache,obs,unibet,errs,attempts,successes,ba,bs,fa,fs=m.fetch_odds(events,__import__('datetime').datetime.now(__import__('datetime').timezone.utc))
  self.assertEqual(attempts,2);self.assertEqual(successes,2);self.assertEqual((ba,bs,fa,fs),(2,2,0,0));self.assertEqual(len(cache),12);self.assertEqual(len(obs),36);self.assertEqual(unibet,[]);self.assertFalse(errs)
 def test_missing_batch_item_falls_back_only_for_missing_event(self):
  events=[event(1),event(2)]
  def fake(path,params):
   if path=='/odds/multi':return [odds(1)]
   self.assertEqual(params['eventId'],'2');self.assertEqual(params['bookmakers'],'Bet365,Unibet');return odds(2)
  with patch.object(m,'get',side_effect=fake):
   cache,obs,unibet,errs,attempts,successes,ba,bs,fa,fs=m.fetch_odds(events,__import__('datetime').datetime.now(__import__('datetime').timezone.utc))
  self.assertEqual((attempts,successes,ba,bs,fa,fs),(2,2,1,1,1,1));self.assertEqual(len(cache),2);self.assertEqual(unibet,[]);self.assertFalse(errs)
 def test_collects_unibet_without_extra_calls(self):
  events=[event(1)]
  with patch.object(m,'get',return_value=[odds_both(1)]) as mocked:
   cache,obs,unibet,errs,attempts,successes,ba,bs,fa,fs=m.fetch_odds(events,__import__('datetime').datetime.now(__import__('datetime').timezone.utc))
  self.assertEqual(mocked.call_count,1);self.assertEqual(attempts,1);self.assertEqual(len(obs),3);self.assertEqual(len(unibet),3);self.assertTrue(all(x['bookmaker']=='Unibet' for x in unibet));self.assertFalse(errs)
 def test_prices_non_h2h_modelled_markets(self):
  event={'home':'Home FC','away':'Away FC'}
  self.assertEqual(m.price_from_market({'market':'totals','pick':'Over','line':2.5},event,{'name':'Totals','odds':[{'total':2.5,'over':'1.91','under':'1.91'}]}),1.91)
  self.assertEqual(m.price_from_market({'market':'btts','pick':'Yes'},event,{'name':'Both Teams To Score','odds':[{'yes':'1.8','no':'2.0'}]}),1.8)
  self.assertEqual(m.price_from_market({'market':'spreads','pick':'Home FC','line':-1.5},event,{'name':'Spread','odds':[{'handicap':-1.5,'home':'2.1','away':'1.7'}]}),2.1)
  self.assertEqual(m.price_from_market({'market':'spreads','pick':'Away FC','line':1.5},event,{'name':'Spread','odds':[{'handicap':-1.5,'home':'2.1','away':'1.7'}]}),1.7)
  self.assertIsNone(m.price_from_market({'market':'totals','pick':'Over','line':3.5},event,{'name':'Totals','odds':[{'total':2.5,'over':'1.91','under':'1.91'}]}))
if __name__=='__main__':unittest.main()
