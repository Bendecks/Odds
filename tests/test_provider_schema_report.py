import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import scripts.provider_schema_report as report


class TestProviderSchemaReport(unittest.TestCase):
    def test_load_rows_skips_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            obs = pathlib.Path(tmp) / 'observations.jsonl'
            obs.write_text('{"market":"Totals"}\nnot-json\n{"market":"Totals","selection":"over"}\n')
            with patch.object(report, 'OBS', obs):
                rows = report.load_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]['selection'], 'over')

    def test_missing_input_returns_empty_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(report, 'OBS', pathlib.Path(tmp) / 'missing.jsonl'):
                self.assertEqual(report.load_rows(), [])

    def test_main_groups_schema_and_bounds_examples(self):
        rows=[]
        for i in range(20):
            rows.append({
                'market':'Exact Total Goals',
                'raw_selection_name':f'name-{i}',
                'raw_selection_label':f'label-{i}',
                'selection':'over' if i % 2 == 0 else 'under',
                'line':i + 0.5,
            })
        rows.append({'market':None,'selection':None})
        with tempfile.TemporaryDirectory() as tmp:
            out=pathlib.Path(tmp) / 'schema.json'
            with patch.object(report,'load_rows',return_value=rows), patch.object(report,'OUT',out):
                report.main()
            data=json.loads(out.read_text())
        self.assertEqual(data['observations'],21)
        exact=data['markets']['Exact Total Goals']
        self.assertEqual(exact['observations'],20)
        self.assertEqual(len(exact['schema_examples']),12)
        self.assertEqual(exact['selection_fields'][0],["over",10])
        self.assertEqual(data['markets']['unknown']['selection_fields'],[["unknown",1]])

    def test_missing_raw_name_and_label_are_not_counted(self):
        rows=[
            {'market':'Totals','selection':'over','line':2.5},
            {'market':'Totals','selection':'under','line':2.5,'raw_selection_name':'','raw_selection_label':None},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out=pathlib.Path(tmp) / 'schema.json'
            with patch.object(report,'load_rows',return_value=rows), patch.object(report,'OUT',out):
                report.main()
            totals=json.loads(out.read_text())['markets']['Totals']
        self.assertEqual(totals['raw_selection_names'],[])
        self.assertEqual(totals['raw_selection_labels'],[])
        self.assertEqual(totals['lines'],[["2.5",2]])


if __name__ == '__main__':
    unittest.main()
