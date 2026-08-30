import pathlib, unittest

class TestRawSnapshotStorage(unittest.TestCase):
    def test_raw_snapshot_is_ignored_by_git(self):
        self.assertIn('data/bet365_observations.jsonl', pathlib.Path('.gitignore').read_text())
    def test_workflow_archives_but_does_not_git_add_raw_snapshot(self):
        src=pathlib.Path('.github/workflows/the_odds_feed.yml').read_text()
        self.assertIn('actions/upload-artifact@v4',src)
        add_lines=[x for x in src.splitlines() if 'git add ' in x]
        self.assertTrue(add_lines)
        self.assertTrue(all('bet365_observations.jsonl' not in x for x in add_lines))

if __name__=='__main__':unittest.main()
