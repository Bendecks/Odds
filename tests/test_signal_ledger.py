import unittest
from scripts.signal_ledger import MAX_ROWS, key

class TestSignalLedger(unittest.TestCase):
    def test_ledger_is_bounded(self): self.assertLessEqual(MAX_ROWS,5000)
    def test_signal_key_changes_with_price(self): self.assertNotEqual(key({'event':'A','odds':2}),key({'event':'A','odds':2.1}))

if __name__=='__main__':unittest.main()
