import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import odds_api_io_bet365 as feed

class ResolverDiagnosticsTests(unittest.TestCase):
    def test_deduplicates_reference_outcomes_by_event(self):
        refs=[
            {'event':'FC Copenhagen vs Brondby IF','pick':'FC Copenhagen','commence_time':'2026-09-01T18:00:00Z'},
            {'event':'FC Copenhagen vs Brondby IF','pick':'Draw','commence_time':'2026-09-01T18:00:00Z'},
            {'event':'FC Copenhagen vs Brondby IF','pick':'Brondby IF','commence_time':'2026-09-01T18:00:00Z'},
        ]
        with patch.object(feed,'conservative_match',return_value={'accepted':False,'reason':'no_candidate'}) as mocked:
            rows,ids,counts,total=feed.resolver_diagnostics(refs,{},[])
        self.assertEqual(total,1); self.assertEqual(mocked.call_count,1); self.assertEqual(len(rows),1); self.assertEqual(counts['no_candidate'],1); self.assertEqual(ids,set())

    def test_same_teams_different_kickoff_are_distinct_events(self):
        refs=[{'event':'A vs B','commence_time':'2026-09-01T18:00:00Z'},{'event':'A vs B','commence_time':'2026-09-08T18:00:00Z'}]
        with patch.object(feed,'conservative_match',return_value={'accepted':False,'reason':'no_candidate'}) as mocked:
            _,_,_,total=feed.resolver_diagnostics(refs,{},[])
        self.assertEqual(total,2); self.assertEqual(mocked.call_count,2)

    def test_clear_bet365_removes_stale_verification_only(self):
        refs=[{'event':'A vs B','fair_probability':0.55,'bet365_verified':True,'bet365_odds':2.1,'bet365_timestamp':'old','bet365_event_id':1,'event_match_method':'exact'}]
        cleaned=feed.clear_bet365(refs)[0]
        self.assertEqual(cleaned['fair_probability'],0.55); self.assertNotIn('bet365_verified',cleaned); self.assertNotIn('bet365_odds',cleaned); self.assertNotIn('event_match_method',cleaned)

    def test_persisted_rows_are_bounded_but_counts_cover_all_events(self):
        refs=[{'event':f'Team {i} vs Rival {i}','commence_time':'2026-09-01T18:00:00Z'} for i in range(6)]
        with patch.object(feed,'MAX_RESOLVER_ROWS',2), patch.object(feed,'conservative_match',return_value={'accepted':False,'reason':'no_candidate'}):
            rows,_,counts,total=feed.resolver_diagnostics(refs,{},[])
        self.assertEqual(total,6); self.assertEqual(len(rows),2); self.assertEqual(counts['no_candidate'],6)

if __name__=='__main__':unittest.main()
