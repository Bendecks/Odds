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
        self.assertEqual(total,1)
        self.assertEqual(mocked.call_count,1)
        self.assertEqual(len(rows),1)
        self.assertEqual(counts['no_candidate'],1)
        self.assertEqual(ids,set())

    def test_persisted_rows_are_bounded_but_counts_cover_all_events(self):
        refs=[{'event':f'Team {i} vs Rival {i}','commence_time':'2026-09-01T18:00:00Z'} for i in range(6)]
        with patch.object(feed,'MAX_RESOLVER_ROWS',2), patch.object(feed,'conservative_match',return_value={'accepted':False,'reason':'no_candidate'}):
            rows,_,counts,total=feed.resolver_diagnostics(refs,{},[])
        self.assertEqual(total,6)
        self.assertEqual(len(rows),2)
        self.assertEqual(counts['no_candidate'],6)

if __name__=='__main__':unittest.main()
