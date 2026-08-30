import unittest
from scripts.the_odds_feed import novig_fair, quality

class TestReferenceFeed(unittest.TestCase):
    def test_novig_three_way_keeps_draw(self):
        fair=novig_fair([{'name':'Home','price':2.0},{'name':'Draw','price':3.0},{'name':'Away','price':4.0}])
        self.assertEqual(set(fair),{'Home','Draw','Away'})
        self.assertAlmostEqual(sum(fair.values()),1.0)
    def test_quality_is_metadata_not_discovery_filter(self):
        self.assertEqual(quality(1),'weak'); self.assertEqual(quality(2),'limited'); self.assertEqual(quality(3),'good'); self.assertEqual(quality(4),'strong')

if __name__=='__main__':unittest.main()
