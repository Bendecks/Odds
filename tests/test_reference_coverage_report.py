import unittest
from scripts.the_odds_feed import quality

class TestReferenceCoverageReport(unittest.TestCase):
    def test_three_books_is_play_depth_boundary(self):
        self.assertEqual(quality(2),'limited'); self.assertEqual(quality(3),'good')

if __name__=='__main__':unittest.main()
