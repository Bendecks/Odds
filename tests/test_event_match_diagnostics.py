import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from event_match_diagnostics import conservative_match, team_similarity


class EventResolverTests(unittest.TestCase):
    def test_normalizes_common_club_noise(self):
        self.assertGreaterEqual(team_similarity('FC Copenhagen', 'Copenhagen'), 0.99)

    def test_accepts_clear_same_time_alias_when_explicitly_probing_lower_threshold(self):
        events=[{'id':'1','home':'Manchester United','away':'Arsenal','date':'2026-08-31T18:00:00Z'}]
        result=conservative_match('Man Utd','Arsenal FC','2026-08-31T18:00:00Z',events,min_team=0.50,min_score=0.70)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['best']['event_id'],'1')

    def test_default_threshold_does_not_accept_aggressive_alias(self):
        events=[{'id':'1','home':'Manchester United','away':'Arsenal','date':'2026-08-31T18:00:00Z'}]
        result=conservative_match('Man Utd','Arsenal FC','2026-08-31T18:00:00Z',events)
        self.assertFalse(result['accepted'])

    def test_rejects_large_kickoff_difference(self):
        events=[{'id':'1','home':'Copenhagen','away':'Brondby','date':'2026-08-31T20:00:00Z'}]
        result=conservative_match('FC Copenhagen','Brondby IF','2026-08-31T18:00:00Z',events)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['reason'],'no_candidate')

    def test_rejects_ambiguous_candidates(self):
        events=[
            {'id':'1','home':'Real Madrid','away':'Barcelona','date':'2026-08-31T18:00:00Z'},
            {'id':'2','home':'Real Madrid CF','away':'FC Barcelona','date':'2026-08-31T18:00:00Z'},
        ]
        result=conservative_match('Real Madrid','Barcelona','2026-08-31T18:00:00Z',events)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['reason'],'ambiguous')


if __name__ == '__main__':
    unittest.main()
