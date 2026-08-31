import sys, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import value_decision_engine as engine

class DecisionIdentityTests(unittest.TestCase):
    def test_qualified_pick_preserves_provider_identity(self):
        now=datetime(2026,8,31,10,0,tzinfo=timezone.utc)
        c={'event':'A vs B','event_id':'ref-123','sport':'soccer_test','commence_time':(now+timedelta(hours=2)).isoformat(),'market':'h2h','pick':'A','fair_probability':0.7,'books':5,'reference_quality':'strong','bet365_verified':True,'bet365_odds':2.0,'bet365_timestamp':(now-timedelta(minutes=1)).isoformat(),'bet365_event_id':987,'model_version':'test-v1'}
        d=engine.decide([c],now)
        self.assertEqual(d['decision'],'PAPER PICK')
        self.assertEqual(d['event_id'],'ref-123')
        self.assertEqual(d['sport'],'soccer_test')
        self.assertEqual(d['bet365_event_id'],987)
        self.assertEqual(d['event_match_method'],'exact')

    def test_explicit_match_method_is_preserved(self):
        now=datetime(2026,8,31,10,0,tzinfo=timezone.utc)
        c={'event':'A vs B','event_id':'ref','sport':'soccer_test','commence_time':(now+timedelta(hours=2)).isoformat(),'market':'h2h','pick':'A','fair_probability':0.7,'books':5,'bet365_verified':True,'bet365_odds':2.0,'bet365_timestamp':now.isoformat(),'bet365_event_id':987,'event_match_method':'provider_exact','model_version':'v'}
        self.assertEqual(engine.decide([c],now)['event_match_method'],'provider_exact')

if __name__=='__main__':unittest.main()
