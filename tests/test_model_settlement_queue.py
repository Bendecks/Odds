import unittest
from scripts.model_settlement_queue import signal_key

class SettlementQueueTests(unittest.TestCase):
    def test_signal_key_is_stable_and_distinguishes_price_time(self):
        a={'event':'A vs B','market':'h2h','pick':'A','price_timestamp':'2026-08-30T10:00:00Z','model_version':'v3'}
        b=dict(a); b['price_timestamp']='2026-08-30T10:01:00Z'
        self.assertEqual(signal_key(a),'A vs B|h2h||A|2026-08-30T10:00:00Z|v3')
        self.assertNotEqual(signal_key(a),signal_key(b))

if __name__=='__main__': unittest.main()
