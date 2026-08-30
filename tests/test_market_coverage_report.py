import unittest
from scripts.market_coverage_report import CORE

class TestMarketCoverage(unittest.TestCase):
    def test_core_market_families_include_liquid_baselines(self):
        self.assertIn('ML',CORE); self.assertIn('Totals',CORE); self.assertIn('Spread',CORE)
    def test_props_do_not_become_core_just_because_they_have_many_lines(self):
        self.assertNotIn('Correct Score',CORE); self.assertNotIn('Player Shots',CORE)

if __name__=='__main__':unittest.main()
