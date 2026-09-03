import pathlib, unittest

class TestFeedWorkflowOrder(unittest.TestCase):
    def test_raw_consumers_run_before_artifact_upload(self):
        src=pathlib.Path('.github/workflows/the_odds_feed.yml').read_text()
        archive=src.index('Archive raw provider snapshot')
        self.assertLess(src.index('python scripts/odds_api_io_reference.py'),archive)
        self.assertLess(src.index('python scripts/market_coverage_report.py'),archive)
        self.assertLess(src.index('python scripts/market_signal_candidates.py'),archive)
        self.assertLess(src.index('python scripts/observation_snapshot.py'),archive)

if __name__=='__main__':unittest.main()
