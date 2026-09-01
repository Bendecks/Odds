import pathlib, unittest

class TestJoinerSafety(unittest.TestCase):
    def test_current_join_is_exact_normalized_home_away(self):
        src=pathlib.Path('scripts/odds_api_io_bet365.py').read_text()
        self.assertIn('def event_key(home,away): return norm(home),norm(away)',src)
        self.assertNotIn('SequenceMatcher',src)
        self.assertIn('TEAM_ALIASES',src)
        self.assertIn("return TEAM_ALIASES.get(key,key)",src)
        self.assertIn('conservative_match(home,away,start,events)',src)

if __name__=='__main__':unittest.main()
