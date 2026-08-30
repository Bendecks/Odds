import unittest
from scripts.value_decision_engine import evaluate, decide

class TestDecisionEngine(unittest.TestCase):
    def test_rejects_no_edge(self):
        x=evaluate({'event':'A-B','pick':'A','odds':2.0,'fair_probability':0.50})
        self.assertFalse(x['qualified'])
    def test_selects_best_qualified(self):
        xs=[{'event':'A-B','pick':'A','odds':2.2,'fair_probability':0.52},{'event':'C-D','pick':'C','odds':2.5,'fair_probability':0.48}]
        self.assertEqual(decide(xs)['decision'],'PLAY')
    def test_empty_is_no_bet(self):
        self.assertEqual(decide([])['decision'],'NO BET')

if __name__=='__main__': unittest.main()
