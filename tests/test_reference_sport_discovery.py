import sys, unittest
from unittest.mock import patch
sys.path.insert(0,'scripts')
import the_odds_feed as feed

class ReferenceSportDiscoveryTests(unittest.TestCase):
    def test_discovers_only_active_non_outright_soccer(self):
        data=[{'key':'soccer_epl','active':True,'has_outrights':False},{'key':'soccer_uefa_champs_league','active':True,'has_outrights':False},{'key':'soccer_epl_winner','active':True,'has_outrights':True},{'key':'basketball_nba','active':True,'has_outrights':False},{'key':'soccer_old','active':False,'has_outrights':False}]
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'MAX_SPORTS',24),patch.object(feed,'SPORTS_PER_RUN',8),patch.object(feed,'get',return_value=(data,{})),patch.object(feed,'rotation_cursor',return_value=0):
            sports,source,pool,_=feed.discover_sports()
        self.assertEqual(set(sports),{'soccer_epl','soccer_uefa_champs_league'});self.assertEqual(pool,sports);self.assertEqual(source,'active-soccer-discovery')

    def test_pool_and_per_run_are_separately_bounded(self):
        data=[{'key':f'soccer_{i:02d}','active':True,'has_outrights':False} for i in range(30)]
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'MAX_SPORTS',20),patch.object(feed,'SPORTS_PER_RUN',6),patch.object(feed,'get',return_value=(data,{})),patch.object(feed,'rotation_cursor',return_value=0):
            sports,_,pool,_=feed.discover_sports()
        self.assertEqual(len(pool),20);self.assertEqual(len(sports),6)

    def test_rotation_advances_tail(self):
        pool=feed.CORE_SPORTS+['soccer_tail_a','soccer_tail_b','soccer_tail_c','soccer_tail_d']
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'SPORTS_PER_RUN',4),patch.object(feed,'rotation_cursor',return_value=0):first,c1=feed.select_sports(pool)
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'SPORTS_PER_RUN',4),patch.object(feed,'rotation_cursor',return_value=c1):second,c2=feed.select_sports(pool)
        self.assertEqual(first[:2],feed.CORE_SPORTS[:2]);self.assertEqual(second[:2],feed.CORE_SPORTS[:2]);self.assertNotEqual(first[2:],second[2:]);self.assertEqual(c2,0)

    def test_override_avoids_discovery_call(self):
        with patch.object(feed,'SPORTS_OVERRIDE','soccer_epl,soccer_denmark_superliga'),patch.object(feed,'MAX_SPORTS',24),patch.object(feed,'SPORTS_PER_RUN',8),patch.object(feed,'get') as mocked:
            sports,source,pool,_=feed.discover_sports()
        mocked.assert_not_called();self.assertEqual(source,'override');self.assertEqual(sports,['soccer_epl','soccer_denmark_superliga']);self.assertEqual(pool,sports)

    def test_falls_back_if_sports_endpoint_fails(self):
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'MAX_SPORTS',3),patch.object(feed,'SPORTS_PER_RUN',3),patch.object(feed,'get',side_effect=RuntimeError('offline')),patch.object(feed,'rotation_cursor',return_value=0):
            sports,source,pool,_=feed.discover_sports()
        self.assertEqual(source,'fallback-defaults');self.assertEqual(len(sports),3);self.assertEqual(len(pool),3)

if __name__=='__main__':unittest.main()
