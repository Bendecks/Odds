import unittest
from unittest.mock import patch
import scripts.the_odds_feed as feed
from scripts.the_odds_feed import market_candidates, novig_fair, quality

class TestReferenceFeed(unittest.TestCase):
    def test_novig_three_way_keeps_draw(self):
        fair=novig_fair([{'name':'Home','price':2.0},{'name':'Draw','price':3.0},{'name':'Away','price':4.0}])
        self.assertEqual(set(fair),{'Home','Draw','Away'})
        self.assertAlmostEqual(sum(fair.values()),1.0)
    def test_quality_is_metadata_not_discovery_filter(self):
        self.assertEqual(quality(1),'weak'); self.assertEqual(quality(2),'limited'); self.assertEqual(quality(3),'good'); self.assertEqual(quality(4),'strong')
    def test_rotation_eventually_covers_every_active_sport(self):
        pool=list(feed.CORE_SPORTS)+[f'soccer_extra_{i}' for i in range(12)]
        seen=set();cursor=0
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'SPORTS_PER_RUN',8):
            for _ in range(12):
                with patch.object(feed,'rotation_cursor',return_value=cursor):
                    selected,cursor=feed.select_sports(pool)
                self.assertLessEqual(len(selected),8);seen.update(selected)
        self.assertEqual(seen,set(pool))
    def test_unselected_default_sports_join_rotation(self):
        pool=list(feed.CORE_SPORTS)+['soccer_extra_a','soccer_extra_b']
        seen=set();cursor=0
        with patch.object(feed,'SPORTS_OVERRIDE',''),patch.object(feed,'SPORTS_PER_RUN',4):
            for _ in range(8):
                with patch.object(feed,'rotation_cursor',return_value=cursor):
                    selected,cursor=feed.select_sports(pool)
                seen.update(selected)
        self.assertEqual(seen,set(pool))
    def test_market_candidates_preserve_modelled_lines(self):
        event={'id':'r1','sport_key':'soccer_test','home_team':'Home','away_team':'Away','commence_time':'2026-09-01T12:00:00Z','bookmakers':[{'key':'pinnacle','markets':[{'key':'totals','outcomes':[{'name':'Over','price':1.91,'point':2.5},{'name':'Under','price':1.91,'point':2.5}]},{'key':'btts','outcomes':[{'name':'Yes','price':1.8},{'name':'No','price':2.0}]}]},{'key':'betfair_ex_eu','markets':[{'key':'totals','outcomes':[{'name':'Over','price':1.95,'point':2.5},{'name':'Under','price':1.87,'point':2.5}]}]}]}
        rows=market_candidates(event)
        total_over=[r for r in rows if r['market']=='totals' and r['pick']=='Over' and r.get('line')==2.5][0]
        self.assertEqual(total_over['books'],2)
        self.assertEqual(total_over['model_version'],'market-consensus-v5')
        self.assertFalse(any(r['market']=='btts' for r in rows))
    def test_derives_double_chance_from_three_way_consensus(self):
        event={'id':'r2','sport_key':'soccer_test','home_team':'Home','away_team':'Away','commence_time':'2026-09-01T12:00:00Z','bookmakers':[{'key':'pinnacle','markets':[{'key':'h2h','outcomes':[{'name':'Home','price':2.0},{'name':'Draw','price':3.5},{'name':'Away','price':4.0}]}]},{'key':'williamhill','markets':[{'key':'h2h','outcomes':[{'name':'Home','price':2.1},{'name':'Draw','price':3.4},{'name':'Away','price':3.8}]}]}]}
        rows=market_candidates(event)
        dc=[r for r in rows if r['market']=='double_chance']
        self.assertEqual({r['pick'] for r in dc},{'1X','12','X2'})
        self.assertTrue(all(r['model_version']=='market-consensus-v5-derived' for r in dc))
        self.assertTrue(all(0 < r['fair_probability'] < 1 for r in dc))

if __name__=='__main__':unittest.main()
