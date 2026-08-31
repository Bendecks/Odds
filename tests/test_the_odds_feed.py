import unittest
from unittest.mock import patch
import scripts.the_odds_feed as feed
from scripts.the_odds_feed import novig_fair, quality

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

if __name__=='__main__':unittest.main()
