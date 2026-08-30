import os, sys, unittest
from unittest.mock import patch
sys.path.insert(0,'scripts')
import the_odds_feed as feed

class ReferenceSportDiscoveryTests(unittest.TestCase):
    def test_discovers_only_active_non_outright_soccer(self):
        data=[
            {'key':'soccer_epl','active':True,'has_outrights':False},
            {'key':'soccer_uefa_champs_league','active':True,'has_outrights':False},
            {'key':'soccer_epl_winner','active':True,'has_outrights':True},
            {'key':'basketball_nba','active':True,'has_outrights':False},
            {'key':'soccer_old','active':False,'has_outrights':False},
        ]
        with patch.object(feed,'SPORTS_OVERRIDE',''), patch.object(feed,'MAX_SPORTS',24), patch.object(feed,'get',return_value=(data,{})):
            sports,source=feed.discover_sports()
        self.assertEqual(sports,['soccer_epl','soccer_uefa_champs_league'])
        self.assertEqual(source,'active-soccer-discovery')

    def test_discovery_is_bounded(self):
        data=[{'key':f'soccer_{i:02d}','active':True,'has_outrights':False} for i in range(30)]
        with patch.object(feed,'SPORTS_OVERRIDE',''), patch.object(feed,'MAX_SPORTS',5), patch.object(feed,'get',return_value=(data,{})):
            sports,_=feed.discover_sports()
        self.assertEqual(len(sports),5)

    def test_override_avoids_discovery_call(self):
        with patch.object(feed,'SPORTS_OVERRIDE','soccer_epl,soccer_denmark_superliga'), patch.object(feed,'MAX_SPORTS',24), patch.object(feed,'get') as mocked:
            sports,source=feed.discover_sports()
        mocked.assert_not_called()
        self.assertEqual(source,'override')
        self.assertEqual(sports,['soccer_epl','soccer_denmark_superliga'])

    def test_falls_back_if_sports_endpoint_fails(self):
        with patch.object(feed,'SPORTS_OVERRIDE',''), patch.object(feed,'MAX_SPORTS',3), patch.object(feed,'get',side_effect=RuntimeError('offline')):
            sports,source=feed.discover_sports()
        self.assertEqual(source,'fallback-defaults')
        self.assertEqual(len(sports),3)

if __name__=='__main__':unittest.main()
