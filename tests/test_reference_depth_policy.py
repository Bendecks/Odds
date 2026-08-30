import pathlib, unittest

class TestReferenceDepthPolicy(unittest.TestCase):
    def test_reference_feed_has_no_three_book_discovery_cutoff(self):
        feed=pathlib.Path('scripts/the_odds_feed.py').read_text(); engine=pathlib.Path('scripts/value_decision_engine.py').read_text()
        self.assertNotIn('len(probs)<3',feed)
        self.assertIn('min_reference_books_for_play',engine)

if __name__=='__main__':unittest.main()
