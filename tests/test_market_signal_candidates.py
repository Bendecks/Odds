import unittest

class TestMarketSignalInventory(unittest.TestCase):
    def test_only_current_reference_family_is_labelled_supported(self):
        supported=lambda market: 'h2h-supported' if market=='ML' else 'unmodelled'
        self.assertEqual(supported('ML'),'h2h-supported')
        self.assertEqual(supported('Totals'),'unmodelled')
        self.assertEqual(supported('Player Shots'),'unmodelled')

if __name__=='__main__':unittest.main()
