import unittest
from scripts.value_decision_engine import evaluate, decide, minimum_odds

class TestDecisionEngine(unittest.TestCase):
    def test_unverified_reference_price_cannot_be_play(self):
        self.assertIsNone(evaluate({'event':'A-B','pick':'A','reference_odds':2.2,'fair_probability':0.52,'bet365_verified':False}))
    def test_rejects_no_edge(self):
        x=evaluate({'event':'A-B','pick':'A','bet365_odds':2.0,'fair_probability':0.50,'bet365_verified':True})
        self.assertFalse(x['qualified'])
    def test_selects_best_verified_qualified(self):
        xs=[{'event':'A-B','pick':'A','bet365_odds':3.0,'fair_probability':0.45,'bet365_verified':True},{'event':'C-D','pick':'C','bet365_odds':3.2,'fair_probability':0.40,'bet365_verified':True}]
        self.assertEqual(decide(xs)['decision'],'PLAY')
    def test_minimum_odds_satisfies_both_gates(self):
        p=.52; o=minimum_odds(p)
        self.assertGreaterEqual(p*o-1, .025-1e-9)
        self.assertGreaterEqual(p-1/o, .02-1e-9)
    def test_empty_is_no_bet(self):
        self.assertEqual(decide([])['decision'],'NO BET')

if __name__=='__main__': unittest.main()
