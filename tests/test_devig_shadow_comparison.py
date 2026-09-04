import json
import pathlib
import tempfile
import unittest

import sys
sys.path.insert(0,'scripts')
import odds_api_io_reference as reference


class DevigShadowComparisonTests(unittest.TestCase):
    def test_power_novig_returns_probabilities_that_sum_to_one(self):
        probs=reference.power_novig({'home':1.80,'draw':3.70,'away':4.80})
        self.assertEqual(set(probs),{'home','draw','away'})
        self.assertAlmostEqual(sum(probs.values()),1.0,places=9)

    def test_shadow_keeps_multiplicative_as_production_method(self):
        prices={'home':1.80,'draw':3.70,'away':4.80}
        production=reference.novig(prices)
        shadow=reference.devig_shadow(prices)
        self.assertEqual(shadow['home']['production_method'],'multiplicative')
        self.assertAlmostEqual(shadow['home']['production_probability'],round(production['home'],6))
        self.assertIn('power_probability',shadow['home'])
        self.assertIn('power_delta',shadow['home'])

    def test_reference_main_writes_shadow_fields_without_changing_fair_probability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            old_paths=(reference.UNIBET,reference.BET365,reference.OUT,reference.SHADOW_OUT)
            try:
                reference.UNIBET=root/'data/unibet_observations.jsonl'
                reference.BET365=root/'data/bet365_observations.jsonl'
                reference.OUT=root/'data/value_candidates.json'
                reference.SHADOW_OUT=root/'output/devig_shadow_comparison.json'
                reference.UNIBET.parent.mkdir()
                rows=[
                    {'event_id':'e1','event':'Home v Away','commence_time':'2026-09-05T12:00:00Z','market':'h2h','line':None,'selection':'home','odds':1.80,'home':'Home','away':'Away'},
                    {'event_id':'e1','event':'Home v Away','commence_time':'2026-09-05T12:00:00Z','market':'h2h','line':None,'selection':'draw','odds':3.70,'home':'Home','away':'Away'},
                    {'event_id':'e1','event':'Home v Away','commence_time':'2026-09-05T12:00:00Z','market':'h2h','line':None,'selection':'away','odds':4.80,'home':'Home','away':'Away'},
                ]
                reference.UNIBET.write_text(''.join(json.dumps(x)+'\n' for x in rows))
                reference.BET365.write_text('')

                reference.main()

                candidates=json.loads(reference.OUT.read_text())
                home=next(x for x in candidates if x['pick']=='Home')
                expected=reference.novig({'home':1.80,'draw':3.70,'away':4.80})['home']
                self.assertEqual(home['devig_method'],'multiplicative')
                self.assertAlmostEqual(home['fair_probability'],round(expected,6))
                self.assertEqual(home['devig_shadow']['production_method'],'multiplicative')
                report=json.loads(reference.SHADOW_OUT.read_text())
                self.assertEqual(report['production_impact'],'none')
                self.assertEqual(report['selections_compared'],3)
            finally:
                reference.UNIBET,reference.BET365,reference.OUT,reference.SHADOW_OUT=old_paths

    def test_feed_workflow_commits_shadow_report(self):
        workflow=pathlib.Path('.github/workflows/the_odds_feed.yml').read_text()
        self.assertIn('output/devig_shadow_comparison.json',workflow)


if __name__=='__main__':
    unittest.main()
