import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import paper_pick_readiness as p


class PaperPickReadinessTests(unittest.TestCase):
    def test_reports_evidence_roles_missing_as_current_pick_bottleneck(self):
        operational = {
            "decision": "NO BET",
            "funnel": {
                "candidate_rows": 579,
                "fair_probability_rows": 579,
                "exact_bet365_rows": 447,
                "fresh_exact_bet365_rows": 447,
                "reference_depth_ready_rows": 0,
                "qualified_now_rows": 0,
            },
        }
        rqg = {
            "fresh_exact_candidates": 447,
            "shadow_ready_candidates": 0,
            "missing_roles": {"external_market_reference": 447, "model_reference": 447},
            "unlock_priorities": {
                "recommended_next_unlock": {"single_role_unlock_possible": False},
                "market_priorities": [
                    {"market": "totals", "fresh_exact_candidates": 230, "shadow_ready_candidates": 0, "missing_roles": {"external_market_reference": 230, "model_reference": 230}},
                    {"market": "h2h", "fresh_exact_candidates": 141, "shadow_ready_candidates": 0, "missing_roles": {"external_market_reference": 141, "model_reference": 141}},
                ],
            },
        }
        report = p.build_report(operational, rqg)
        self.assertEqual(report["mode"], "OBSERVABILITY_ONLY")
        self.assertEqual(report["production_impact"], "none")
        self.assertEqual(report["stage"], "evidence_roles_missing")
        self.assertEqual(report["candidate_base"]["fresh_exact_bet365_rows"], 447)
        self.assertEqual(report["candidate_base"]["reference_quality_shadow_ready_rows"], 0)
        self.assertEqual(report["near_term_unlock"]["largest_market"], "totals")
        self.assertEqual(report["near_term_unlock"]["potential_candidates_if_both_roles_added"], 447)
        self.assertIn("edge/EV/stake", report["near_term_unlock"]["note"])

    def test_main_writes_public_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            op = root / "operational.json"
            rqg = root / "rqg.json"
            out = root / "paper_pick_readiness.json"
            op.write_text(json.dumps({"decision": "NO BET", "funnel": {"candidate_rows": 1}}))
            rqg.write_text(json.dumps({}))
            old = (p.OPERATIONAL, p.REFERENCE_QUALITY, p.OUT)
            p.OPERATIONAL, p.REFERENCE_QUALITY, p.OUT = op, rqg, out
            try:
                p.main()
                data = json.loads(out.read_text())
            finally:
                p.OPERATIONAL, p.REFERENCE_QUALITY, p.OUT = old
            self.assertEqual(data["current_decision"], "NO BET")
            self.assertIn("candidate_base", data)


if __name__ == "__main__":
    unittest.main()
