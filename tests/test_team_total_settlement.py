import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import model_settlement_fetch as s

class TeamTotalSettlementTests(unittest.TestCase):
    def row(self,market,pick,line):return {'event':'Home FC vs Away FC','market':market,'pick':pick,'line':line}
    def test_home_half_line(self):
        self.assertEqual(s.market_outcome(self.row('team_total_goals_home','over',1.5),(2,1)),'win')
        self.assertEqual(s.market_outcome(self.row('team_total_goals_home','under',1.5),(2,1)),'loss')
    def test_away_half_line(self):
        self.assertEqual(s.market_outcome(self.row('team_total_goals_away','under',2.5),(3,2)),'win')
        self.assertEqual(s.market_outcome(self.row('team_total_goals_away','over',2.5),(3,2)),'loss')
    def test_integer_and_quarter_lines_fail_closed(self):
        for line in (1.0,1.25,1.75,2.0,2.25):
            self.assertIsNone(s.market_outcome(self.row('team_total_goals_home','over',line),(3,1)))
    def test_aliases_supported(self):
        self.assertTrue(s.supported_market(self.row('team total goals home','over',0.5)))
        self.assertTrue(s.supported_market(self.row('team total goals away','under',0.5)))

if __name__=='__main__':unittest.main()
