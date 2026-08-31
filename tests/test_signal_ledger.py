import unittest
from scripts.signal_ledger import MAX_ROWS, decision_rows, key

class TestSignalLedger(unittest.TestCase):
    def test_ledger_is_bounded(self): self.assertLessEqual(MAX_ROWS,5000)
    def test_signal_key_changes_with_price(self): self.assertNotEqual(key({'event':'A','odds':2}),key({'event':'A','odds':2.1}))
    def test_expands_multi_pick_decision(self):
        rows=decision_rows({'decision':'PAPER PICK','picks':[{'decision':'PAPER PICK','event':'A vs B','market':'h2h','pick':'A','odds':2,'price_timestamp':'t1','model_version':'m'},{'decision':'PAPER PICK','event':'C vs D','market':'totals','pick':'Over','line':2.5,'odds':2.1,'price_timestamp':'t2','model_version':'m'}]},'now')
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r.get('signal_key') for r in rows))

if __name__=='__main__':unittest.main()
