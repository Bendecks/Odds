import pathlib
import unittest


class DevigPagesTests(unittest.TestCase):
    def test_pages_workflow_publishes_shadow_report_when_present(self):
        workflow=pathlib.Path('.github/workflows/pages.yml').read_text()
        self.assertIn('output/devig_shadow_comparison.json',workflow)
        self.assertIn('2>/dev/null || true',workflow)

    def test_dashboard_has_shadow_report_mount_point(self):
        html=pathlib.Path('index.html').read_text()
        self.assertIn('id="devig-shadow"',html)
        self.assertIn('shadowBox',html)
        self.assertIn('id="quota-budget"',html)

    def test_dashboard_loads_shadow_report_fail_soft(self):
        app=pathlib.Path('app.js').read_text()
        self.assertIn('loadDevigShadow',app)
        self.assertIn('output/devig_shadow_comparison.json',app)
        self.assertIn('production_impact',app)
        self.assertIn('rapporten vises efter næste feed-kørsel',app)
        self.assertIn('quota_budget',app)
        self.assertIn('Quota budget:',app)

    def test_shadow_report_has_dashboard_styles(self):
        styles=pathlib.Path('styles.css').read_text()
        self.assertIn('.shadowBox',styles)
        self.assertIn('.shadowMetrics',styles)


if __name__=='__main__':
    unittest.main()
