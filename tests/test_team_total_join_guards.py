import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import derived_market_join as j

class TeamTotalJoinGuardTests(unittest.TestCase):
 def test_valid_half_line_semantics(self):
  self.assertTrue(j.valid_team_total_candidate({'line':1.5,'market_semantics':'binary_half_line_no_push'}))
 def test_requires_semantics(self):
  self.assertFalse(j.valid_team_total_candidate({'line':1.5}))
 def test_rejects_wrong_semantics(self):
  self.assertFalse(j.valid_team_total_candidate({'line':1.5,'market_semantics':'push_on_integer'}))
 def test_rejects_nonpositive_half_line(self):
  self.assertFalse(j.valid_team_total_candidate({'line':-0.5,'market_semantics':'binary_half_line_no_push'}))
 def test_rejects_integer_and_quarter_lines(self):
  for line in (1,1.25,1.75):
   self.assertFalse(j.valid_team_total_candidate({'line':line,'market_semantics':'binary_half_line_no_push'}))
 def test_norm_line_rejects_bool(self):
  self.assertIsNone(j.norm_line(True))

if __name__=='__main__':unittest.main()
