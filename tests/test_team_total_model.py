import math, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import derived_goal_markets as g

class TeamTotalModelTests(unittest.TestCase):
    def test_half_line_probabilities_sum_to_one(self):
        for lam in (0.4,1.0,1.7,3.2):
            for line in g.TEAM_TOTAL_HALF_LINES:
                p=g.team_total_half_line_probabilities(lam,line)
                self.assertAlmostEqual(p['over']+p['under'],1.0,places=12)
                self.assertGreater(p['over'],0);self.assertGreater(p['under'],0)

    def test_over_05_matches_scoring_probability(self):
        for lam in (0.5,1.4,2.8):
            p=g.team_total_half_line_probabilities(lam,0.5)
            self.assertAlmostEqual(p['over'],1-math.exp(-lam),places=12)

    def test_rejects_push_and_split_lines(self):
        for line in (0,1.0,1.25,1.75,2.0,2.25):
            with self.assertRaises(ValueError):g.team_total_half_line_probabilities(1.5,line)

if __name__=='__main__':unittest.main()
