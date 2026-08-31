import importlib.util, json, pathlib, tempfile, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('closing_price_ledger',ROOT/'scripts'/'closing_price_ledger.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ClosingPriceLedgerTests(unittest.TestCase):
    def test_signal_odds_uses_canonical_signal_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'signals.jsonl'
            p.write_text(json.dumps({'signal_key':'a','odds':2.0})+'\n'+json.dumps({'signal_key':'a','odds':2.2})+'\n'+json.dumps({'signal_key':'bad','odds':1.0})+'\n')
            old=m.SIGNALS;m.SIGNALS=p
            try:self.assertEqual(m.signal_odds(),{'a':2.2})
            finally:m.SIGNALS=old

    def test_clv_ignores_duplicated_taken_odds_in_close_row(self):
        with tempfile.TemporaryDirectory() as td:
            td=pathlib.Path(td); signals=td/'signals.jsonl'; closes=td/'closes.jsonl'; status=td/'status.json'
            signals.write_text(json.dumps({'signal_key':'a','odds':2.0})+'\n')
            closes.write_text(json.dumps({'signal_key':'a','taken_odds':9.9,'closing_odds':1.8})+'\n')
            old=(m.SIGNALS,m.PATH,m.STATUS);m.SIGNALS,m.PATH,m.STATUS=signals,closes,status
            try:
                m.main(); row=json.loads(closes.read_text().strip()); self.assertEqual(row['taken_odds'],2.0); self.assertAlmostEqual(row['clv_pct'],(2.0/1.8-1)*100,places=4)
            finally:m.SIGNALS,m.PATH,m.STATUS=old

if __name__=='__main__':unittest.main()
