import pathlib, unittest

class TestPipelineContract(unittest.TestCase):
    def test_reference_feed_does_not_hard_filter_draw_or_three_books(self):
        src=pathlib.Path('scripts/the_odds_feed.py').read_text()
        self.assertNotIn("name.lower()=='draw'",src)
        self.assertNotIn('len(probs)<3',src)
    def test_play_gate_still_requires_reference_depth(self):
        src=pathlib.Path('scripts/value_decision_engine.py').read_text()
        self.assertIn('min_reference_books_for_play',src)

if __name__=='__main__':unittest.main()
