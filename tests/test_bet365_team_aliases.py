import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import odds_api_io_bet365 as b

class Bet365TeamAliasTests(unittest.TestCase):
 def test_observed_provider_aliases_are_exact_keys(self):
  pairs=[
   ('Flamengo','CR Flamengo RJ'),('Mirassol','Mirassol FC SP'),
   ('Real Betis','Real Betis Seville'),('Anderlecht','RSC Anderlecht'),
   ('Liverpool','Liverpool FC'),('FC Zwolle','PEC Zwolle'),
   ('Austria Wien','FK Austria Wien'),('Lyngby','Lyngby BK'),
   ('Sint Truiden','St. Truidense VV'),('Toulouse','Toulouse FC'),
   ('Lille','Lille OSC'),('Botafogo-SP','Botafogo FC SP')]
  for reference,provider in pairs:
   with self.subTest(reference=reference):self.assertEqual(b.norm(reference),b.norm(provider))
 def test_unlisted_names_do_not_become_fuzzy_exact(self):
  self.assertNotEqual(b.norm('Londrina'),b.norm('Londrina EC PR'))
  self.assertNotEqual(b.norm('Juventude'),b.norm('EC Juventude RS'))
if __name__=='__main__':unittest.main()
