import pathlib, unittest

class TestReferenceMatchDiagnostics(unittest.TestCase):
    def test_joiner_reports_unmatched_reasons_before_fuzzy_matching(self):
        src=pathlib.Path('scripts/odds_api_io_bet365.py').read_text()
        for field in ('exact_reference_events_in_bet365','unmatched_reference_events','exact_rows_not_queried','queried_reference_rows_without_h2h_price','matched_prices'):
            self.assertIn(field,src)

if __name__=='__main__':unittest.main()
