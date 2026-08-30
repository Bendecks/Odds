import pathlib, unittest

class TestStorageContract(unittest.TestCase):
    def test_workflow_keeps_compact_history_and_summaries(self):
        src=pathlib.Path('.github/workflows/the_odds_feed.yml').read_text()
        for path in ('data/observation_snapshots.jsonl','data/model_signals.jsonl','output/market_coverage_report.json','output/market_signal_inventory.json'):
            self.assertIn(path,src)

if __name__=='__main__':unittest.main()
