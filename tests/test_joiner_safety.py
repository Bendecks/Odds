import pathlib, unittest

class TestJoinerSafety(unittest.TestCase):
    def test_current_join_is_exact_normalized_home_away(self):
        src=pathlib.Path('scripts/odds_api_io_bet365.py').read_text()
        self.assertIn('def event_key(home,away): return norm(home),norm(away)',src)
        self.assertNotIn('SequenceMatcher',src)
        self.assertNotIn('fuzzy',src.lower())

if __name__=='__main__':unittest.main()
