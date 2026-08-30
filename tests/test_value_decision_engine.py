import unittest
from datetime import datetime, timezone, timedelta
from scripts.value_decision_engine import evaluate, decide, minimum_odds

NOW=datetime(2026,8,30,8,0,tzinfo=timezone.utc)
def row(odds,p): return {'event':'A-B','pick':'A','bet365_odds':odds,'fair_probability':p,'bet365_verified':True,'bet365_timestamp':NOW.isoformat(),'commence_time':(NOW+timedelta(hours=3)).isoformat()}

class TestDecisionEngine(unittest.TestCase):
    def test_unverified_reference_price_cannot_be_play(self): self.assertIsNone(evaluate({'event':'A-B','pick':'A','reference_odds':2.2,'fair_probability':0.52,'bet365_verified':False},NOW))
    def test_rejects_no_edge(self): self.assertFalse(evaluate(row(2.0,.50),NOW)['qualified'])
    def test_selects_best_verified_qualified_in_paper_mode(self): self.assertEqual(decide([row(3.0,.45),row(3.2,.40)],NOW)['decision'],'PAPER PICK')
    def test_stale_price_is_rejected(self):
        x=row(3.0,.45); x['bet365_timestamp']=(NOW-timedelta(minutes=21)).isoformat(); self.assertIsNone(evaluate(x,NOW))
    def test_minimum_odds_satisfies_both_gates(self):
        p=.52; o=minimum_odds(p); self.assertGreaterEqual(p*o-1,.025-1e-9); self.assertGreaterEqual(p-1/o,.02-1e-9)
    def test_empty_is_no_bet(self): self.assertEqual(decide([],NOW)['decision'],'NO BET')

if __name__=='__main__':unittest.main()
