import unittest
from scripts.observation_snapshot import MAX_SNAPSHOTS

class TestObservationSnapshot(unittest.TestCase):
    def test_history_is_bounded(self): self.assertGreaterEqual(MAX_SNAPSHOTS,60); self.assertLessEqual(MAX_SNAPSHOTS,365)

if __name__=='__main__':unittest.main()
