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

    def test_full_pool_is_preserved_while_paid_requests_are_bounded(self):
        data=[{'key':f'soccer_{i:02d}','active':True,'has_outrights':False} for i in range(30)]
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'MAX_SPORTS',20),patch.object(feed,'SPORTS_PER_RUN',6),patch.object(feed,'get',return_value=(data,{})),patch.object(feed,'rotation_cursor',return_value=0):
            sports,_,pool,_=feed.discover_sports()
        self.assertEqual(len(pool),30);self.assertEqual(len(sports),6)

    def test_rotation_advances_across_all_nonstable_sports(self):
        pool=feed.CORE_SPORTS+['soccer_tail_a','soccer_tail_b','soccer_tail_c','soccer_tail_d']
        seen=set();cursor=0
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'SPORTS_PER_RUN',4):
            for _ in range(6):
                with patch.object(feed,'rotation_cursor',return_value=cursor):selected,cursor=feed.select_sports(pool)
                self.assertEqual(selected[:2],feed.CORE_SPORTS[:2]);self.assertLessEqual(len(selected),4);seen.update(selected)
        self.assertEqual(seen,set(pool))

    def test_override_avoids_discovery_call(self):
        with patch.object(feed,'SPORTS_OVERRIDE','soccer_epl,soccer_denmark_superliga'),patch.object(feed,'MAX_SPORTS',24),patch.object(feed,'SPORTS_PER_RUN',8),patch.object(feed,'get') as mocked:
            sports,source,pool,_=feed.discover_sports()
        mocked.assert_not_called();self.assertEqual(source,'override');self.assertEqual(sports,['soccer_epl','soccer_denmark_superliga']);self.assertEqual(pool,sports)

    def test_falls_back_if_sports_endpoint_fails(self):
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'MAX_SPORTS',3),patch.object(feed,'SPORTS_PER_RUN',3),patch.object(feed,'get',side_effect=RuntimeError('offline')),patch.object(feed,'rotation_cursor',return_value=0):
            sports,source,pool,_=feed.discover_sports()
        self.assertEqual(source,'fallback-defaults');self.assertEqual(len(sports),3);self.assertEqual(len(pool),3)

if __name__=='__main__':unittest.main()
