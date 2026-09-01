import pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import derived_goal_markets as g

class GoalMarketCandidateTests(unittest.TestCase):
    def rows(self):
        common={'event':'Home FC vs Away FC','event_id':'e1','sport':'soccer_test','commence_time':'2026-09-02T18:00:00Z','books':4}
        return [
            {**common,'market':'h2h','pick':'Home FC','fair_probability':0.45},
            {**common,'market':'h2h','pick':'Draw','fair_probability':0.27},
            {**common,'market':'h2h','pick':'Away FC','fair_probability':0.28},
            {**common,'market':'totals','pick':'Over','line':2.5,'fair_probability':0.52},
            {**common,'market':'totals','pick':'Under','line':2.5,'fair_probability':0.48},
        ]

    def test_derives_all_safe_goal_market_families(self):
        out=g.derive_for_event(self.rows())
        markets={r['market'] for r in out}
        self.assertEqual(markets,set(g.MARKETS))
        self.assertEqual(sum(r['market']=='odd_even' for r in out),2)
        self.assertEqual(sum(r['market']=='clean_sheet_home' for r in out),2)
        self.assertEqual(sum(r['market']=='clean_sheet_away' for r in out),2)
        self.assertEqual(sum(r['market']=='exact_total_goals' for r in out),7)
        self.assertEqual(sum(r['market']=='home_exact_goals' for r in out),5)
        self.assertEqual(sum(r['market']=='away_exact_goals' for r in out),5)

    def test_candidates_start_unverified(self):
        out=g.derive_for_event(self.rows())
        self.assertTrue(out)
        self.assertTrue(all(r['bet365_verified'] is False for r in out))
        self.assertTrue(all(r['bookmaker']=='DERIVED_REFERENCE_MARKET' for r in out))
        self.assertTrue(all(r['model_fit_rmse']<=g.MAX_RMSE for r in out))

    def test_exact_goal_candidates_have_integer_line(self):
        out=g.derive_for_event(self.rows())
        exact=[r for r in out if r['market'] in ('exact_total_goals','home_exact_goals','away_exact_goals')]
        self.assertTrue(exact)
        self.assertTrue(all(isinstance(r.get('line'),int) and r['line']>=0 for r in exact))

if __name__=='__main__':unittest.main()
