import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import model_settlement_fetch as fetch

class ModelSettlementFetchTests(unittest.TestCase):
    def row(self,pick='A'):return {'event':'A vs B','pick':pick,'market':'h2h'}
    def test_home_win(self):self.assertEqual(fetch.outcome(self.row('A'),{'status':'settled','scores':{'home':2,'away':1}}),'win')
    def test_away_loss(self):self.assertEqual(fetch.outcome(self.row('B'),{'status':'settled','scores':{'home':2,'away':1}}),'loss')
    def test_draw_pick(self):self.assertEqual(fetch.outcome(self.row('Draw'),{'status':'settled','scores':{'home':1,'away':1}}),'win')
    def test_total_goals_market(self):
        self.assertEqual(fetch.outcome({'event':'A vs B','market':'totals','pick':'Over','line':2.5},{'status':'settled','scores':{'home':2,'away':1}}),'win')
        self.assertEqual(fetch.outcome({'event':'A vs B','market':'totals','pick':'Under','line':2.5},{'status':'settled','scores':{'home':2,'away':1}}),'loss')
        self.assertEqual(fetch.outcome({'event':'A vs B','market':'totals','pick':'Over','line':3.0},{'status':'settled','scores':{'home':2,'away':1}}),'push')
    def test_btts_market(self):
        self.assertEqual(fetch.outcome({'event':'A vs B','market':'btts','pick':'Yes'},{'status':'settled','scores':{'home':2,'away':1}}),'win')
        self.assertEqual(fetch.outcome({'event':'A vs B','market':'btts','pick':'No'},{'status':'settled','scores':{'home':2,'away':1}}),'loss')
    def test_spread_market(self):
        self.assertEqual(fetch.outcome({'event':'A vs B','market':'spreads','pick':'A','line':-1.5},{'status':'settled','scores':{'home':3,'away':1}}),'win')
        self.assertEqual(fetch.outcome({'event':'A vs B','market':'spreads','pick':'B','line':1.5},{'status':'settled','scores':{'home':3,'away':1}}),'loss')
    def test_cancelled_is_void(self):self.assertEqual(fetch.outcome(self.row(),{'status':'cancelled'}),'void')
    def test_postponed_is_void(self):self.assertEqual(fetch.outcome(self.row(),{'status':'postponed'}),'void')
    def test_pending_is_not_settled(self):self.assertIsNone(fetch.outcome(self.row(),{'status':'pending','scores':{'home':0,'away':0}}))
    def test_unknown_pick_is_not_guessed(self):self.assertIsNone(fetch.outcome(self.row('C'),{'status':'settled','scores':{'home':1,'away':0}}))
    def test_wrapped_event_and_flat_scores(self):self.assertEqual(fetch.outcome(self.row('A'),{'data':{'status':'completed','homeScore':3,'awayScore':0}}),'win')
    def test_regulation_ft_beats_extra_time_top_level(self):
        event={'status':'settled','scores':{'home':2,'away':1,'periods':{'ft':{'home':1,'away':1},'et':{'home':1,'away':0}}}}
        self.assertEqual(fetch.outcome(self.row('Draw'),event),'win')
        self.assertEqual(fetch.outcome(self.row('A'),event),'loss')
        self.assertEqual(fetch.score_source(event),'regulation_ft')
    def test_full_time_alias(self):
        event={'status':'finished','scores':{'home':3,'away':2,'periods':{'full_time':{'home':2,'away':2}}}}
        self.assertEqual(fetch.score_pair(event),(2.0,2.0))
    def test_extra_time_without_regulation_score_fails_closed(self):
        event={'status':'settled','scores':{'home':2,'away':1,'periods':{'et':{'home':1,'away':0}}}}
        self.assertTrue(fetch.has_extra_time_or_penalties(event))
        self.assertEqual(fetch.settlement_score_pair(event),(None,'ambiguous_knockout_score'))
        self.assertIsNone(fetch.outcome(self.row('A'),event))
    def test_penalty_shootout_without_regulation_score_fails_closed(self):
        event={'status':'finished','scores':{'home':5,'away':4,'periods':{'penalties':{'home':5,'away':4}}}}
        self.assertEqual(fetch.settlement_score_pair(event),(None,'ambiguous_knockout_score'))
        self.assertIsNone(fetch.outcome(self.row('A'),event))
    def test_regulation_score_allows_settlement_despite_penalties(self):
        event={'status':'finished','scores':{'home':5,'away':4,'periods':{'ft':{'home':1,'away':1},'penalties':{'home':4,'away':3}}}}
        self.assertEqual(fetch.settlement_score_pair(event),((1.0,1.0),'regulation_ft'))
        self.assertEqual(fetch.outcome(self.row('Draw'),event),'win')
    def test_existing_keys_require_valid_settlement(self):
        valid={'signal_key':'A vs B|h2h|A|2026-08-31T10:00:00Z|v1','event':'A vs B','market':'h2h','pick':'A','price_timestamp':'2026-08-31T10:00:00Z','model_version':'v1','result':'win','odds':2.0,'stake_dkk':1.0}
        self.assertIn(valid['signal_key'],fetch.existing_keys([valid]))
        self.assertEqual(fetch.existing_keys([{'signal_key':'x','result':'pending'}]),set())

if __name__=='__main__':unittest.main()
