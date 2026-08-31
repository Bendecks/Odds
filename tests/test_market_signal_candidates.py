import unittest
from scripts.market_signal_candidates import reference_model_status

class TestMarketSignalInventory(unittest.TestCase):
    def test_modelled_reference_families_are_labelled_supported(self):
        self.assertEqual(reference_model_status('ML'),'reference-supported')
        self.assertEqual(reference_model_status('Totals'),'reference-supported')
        self.assertEqual(reference_model_status('Spread'),'reference-supported')
        self.assertEqual(reference_model_status('Both Teams To Score'),'reference-supported')
        self.assertEqual(reference_model_status('Player Shots'),'unmodelled')

if __name__=='__main__':unittest.main()
