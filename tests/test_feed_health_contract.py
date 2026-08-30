import pathlib, unittest

class TestFeedHealthContract(unittest.TestCase):
    def test_no_bet_does_not_fail_workflow(self):
        src=pathlib.Path('scripts/value_decision_engine.py').read_text()
        self.assertIn("'decision':'NO BET'",src)
        workflow=pathlib.Path('.github/workflows/the_odds_feed.yml').read_text()
        self.assertIn('python scripts/value_decision_engine.py',workflow)

if __name__=='__main__':unittest.main()
