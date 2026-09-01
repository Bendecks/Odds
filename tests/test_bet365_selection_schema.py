import pathlib,sys,unittest
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import odds_api_io_bet365 as b

class Bet365SelectionSchemaTests(unittest.TestCase):
 def test_market_rows_preserve_raw_selection_metadata(self):
  event={'id':'e1','home':'A','away':'B','sport':'football','league':'L','date':'2026-09-02T12:00:00Z'}
  markets=[{'name':'Exact Goals','updatedAt':'2026-09-01T10:00:00Z','odds':[{'name':'2 Goals','label':'Two','handicap':2,'odds':3.4}]}]
  rows=b.market_rows(event,markets,datetime(2026,9,1,tzinfo=timezone.utc))
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['selection'],'odds')
  self.assertEqual(rows[0]['raw_selection_name'],'2 Goals')
  self.assertEqual(rows[0]['raw_selection_label'],'Two')
  self.assertEqual(rows[0]['line'],2)
if __name__=='__main__':unittest.main()
