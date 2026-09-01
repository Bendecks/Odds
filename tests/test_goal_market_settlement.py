import pathlib, sys, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import model_settlement_fetch as m


class GoalMarketSettlementTests(unittest.TestCase):
    def row(self, market, pick, line=None):
        out={'market':market,'pick':pick,'event':'Home FC vs Away FC'}
        if line is not None:out['line']=line
        return out

    def test_odd_even(self):
        self.assertEqual(m.market_outcome(self.row('odd_even','Odd'),(2,1)),'win')
        self.assertEqual(m.market_outcome(self.row('odd_even','Even'),(2,1)),'loss')
        self.assertEqual(m.market_outcome(self.row('Odd/Even','Even'),(2,2)),'win')

    def test_clean_sheet_home_uses_away_goals(self):
        self.assertEqual(m.market_outcome(self.row('clean_sheet_home','Yes'),(3,0)),'win')
        self.assertEqual(m.market_outcome(self.row('clean_sheet_home','Yes'),(0,1)),'loss')
        self.assertEqual(m.market_outcome(self.row('Clean Sheet Home','No'),(1,2)),'win')

    def test_clean_sheet_away_uses_home_goals(self):
        self.assertEqual(m.market_outcome(self.row('clean_sheet_away','Yes'),(0,2)),'win')
        self.assertEqual(m.market_outcome(self.row('clean_sheet_away','Yes'),(1,0)),'loss')

    def test_exact_total_goals(self):
        self.assertEqual(m.market_outcome(self.row('exact_total_goals','3'),(2,1)),'win')
        self.assertEqual(m.market_outcome(self.row('Exact Total Goals','4'),(2,1)),'loss')

    def test_team_exact_goals(self):
        self.assertEqual(m.market_outcome(self.row('home_exact_goals','2'),(2,3)),'win')
        self.assertEqual(m.market_outcome(self.row('Home Team Exact Goals','1'),(2,3)),'loss')
        self.assertEqual(m.market_outcome(self.row('away_exact_goals','3'),(2,3)),'win')
        self.assertEqual(m.market_outcome(self.row('Away Team Exact Goals','2'),(2,3)),'loss')

    def test_exact_goal_pick_rejects_non_integer_or_negative(self):
        self.assertIsNone(m.exact_goal_pick(self.row('exact_total_goals','2.5')))
        self.assertIsNone(m.exact_goal_pick(self.row('exact_total_goals','-1')))
        self.assertEqual(m.exact_goal_pick(self.row('exact_total_goals','3')),3)

    def test_new_markets_are_supported(self):
        for market in ('odd_even','clean_sheet_home','clean_sheet_away','exact_total_goals','home_exact_goals','away_exact_goals'):
            self.assertTrue(m.supported_market(self.row(market,'Yes')))


if __name__=='__main__':unittest.main()
