import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import date

from catalog_guard.core import InputError, analyze, config_checked, load_rows
from catalog_guard.cli import main, render_html

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 23)


class CatalogTests(unittest.TestCase):
    def codes(self, rows, config=None, baseline=None):
        return {x['code'] for x in analyze(rows, config or {'id': 'id'}, baseline, TODAY)['findings']}

    def test_good_example(self):
        config = json.loads((ROOT / 'examples/rules.json').read_text())
        report = analyze(load_rows(ROOT / 'examples/good.csv'), config, today=TODAY)
        self.assertEqual((report['errors'], report['warnings']), (0, 0))

    def test_broken_example(self):
        config = json.loads((ROOT / 'examples/rules.json').read_text())
        self.assertEqual(self.codes(load_rows(ROOT / 'examples/broken.json'), config),
                         {'duplicate_id', 'required', 'url', 'missing_evidence', 'verification_conflict', 'stale'})

    def test_empty_is_error(self):
        self.assertIn('empty_catalog', self.codes([]))

    def test_ids_must_be_unambiguous(self):
        for value in (None, '', ' ', 1, True, ' a'):
            with self.subTest(value=value):
                self.assertIn('invalid_id', self.codes([{'id': value}]))

    def test_duplicate_disables_diff(self):
        report = analyze([{'id': 'a'}, {'id': 'a'}], {'id': 'id'}, [{'id': 'a'}])
        self.assertIsNone(report['diff'])
        self.assertIn('diff_unavailable', {i['code'] for i in report['findings']})

    def test_invalid_baseline_disables_diff(self):
        self.assertIn('baseline_duplicate_id', self.codes([{'id': 'a'}], baseline=[{'id': 'a'}, {'id': 'a'}]))

    def test_diff(self):
        report = analyze([{'id': 'a', 'x': 2}, {'id': 'c'}], {'id': 'id'}, [{'id': 'a', 'x': 1}, {'id': 'b'}])
        self.assertEqual(report['diff'], {'added': ['c'], 'removed': ['b'], 'changed': [{'id': 'a', 'fields': ['x']}], 'removed_fraction': .5})
        self.assertEqual(report['errors'], 1)

    def test_missing_vs_null_diff(self):
        report = analyze([{'id': 'a', 'x': None}], {'id': 'id'}, [{'id': 'a'}])
        self.assertEqual(report['diff']['changed'][0]['fields'], ['x'])

    def test_scalar_type_changes(self):
        for old, new in [(True, 1), (1, 1.0), (1, "1")]:
            report = analyze([{'id': 'a', 'x': new}], {'id': 'id'}, [{'id': 'a', 'x': old}])
            self.assertEqual(report['diff']['changed'][0]['fields'], ['x'])

    def test_removal_boundary(self):
        self.assertNotIn('mass_removal', self.codes([{'id': 'a'}], {'id': 'id', 'max_removed_fraction': .5}, [{'id': 'a'}, {'id': 'b'}]))

    def test_all_removed(self):
        self.assertTrue({'empty_catalog', 'mass_removal'} <= self.codes([], baseline=[{'id': 'a'}]))

    def test_dates(self):
        cfg = {'id': 'id', 'freshness': {'field': 'date', 'max_age_days': 30}}
        for value, expected in [('2026-10-24', 'future_date'), ('2026-09-22', 'stale'), ('2026-02-30', 'date'), (None, 'date'), ('20261023', 'date')]:
            with self.subTest(value=value):
                self.assertIn(expected, self.codes([{'id': 'a', 'date': value}], cfg))
        self.assertEqual(self.codes([{'id': 'a', 'date': '2026-09-23'}], cfg), set())

    def test_urls(self):
        cfg = {'id': 'id', 'urls': ['url']}
        for value in ['file:///etc/passwd', 'https://a:bad', 'https://user:pass@example.org', 'https://[', 'https://a b']:
            self.assertIn('url', self.codes([{'id': 'a', 'url': value}], cfg))
        self.assertEqual(self.codes([{'id': 'a', 'url': 'https://example.org'}], cfg), set())

    def test_configs_fail_closed(self):
        for cfg in [{}, {'id': 'a', 'typo': []}, {'id': 'a', 'required': 'name'}, {'id': 'a', 'max_removed_fraction': True},
                    {'id': 'a', 'freshness': {'field': 'date', 'max_age_days': -1}}, {'id': 'a', 'enums': {'status': []}},
                    {'id': 'a', 'verification': {}}]:
            with self.subTest(cfg=cfg), self.assertRaises(InputError):
                config_checked(cfg)

    def test_reader_rejects_ambiguous_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, content in [('a.json', '[{"id":"a","id":"b"}]'), ('a.json', '[{"id":NaN}]'),
                                  ('a.json', '{}'), ('a.json', '[{"id":{"a":1}}]'), ('a.csv', 'id,id\na,b\n'),
                                  ('a.csv', 'id,x\na\n'), ('a.csv', 'id\na,b\n')]:
                path = Path(tmp) / name
                path.write_text(content)
                with self.subTest(content=content), self.assertRaises(InputError):
                    load_rows(path)

    def test_bom_and_quoted_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'a.csv'
            path.write_text('\ufeffid,name\na,"Hello, 世界"\n', encoding='utf-8')
            self.assertEqual(load_rows(path), [{'id': 'a', 'name': 'Hello, 世界'}])

    def test_html_escapes_untrusted_content(self):
        report = analyze([{'id': '<script>alert(1)</script>'}], {'id': 'id'}, [])
        rendered = render_html(report)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_cli_exit_codes(self):
        common = ['--config', str(ROOT / 'examples/rules.json'), '--today', '2026-10-23']
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(ROOT / 'examples/good.csv')] + common), 0)
            self.assertEqual(main([str(ROOT / 'examples/broken.json')] + common), 1)
            self.assertEqual(main([str(ROOT / 'examples/missing.json')] + common), 2)
            self.assertEqual(main([str(ROOT / 'examples/good.csv')] + common[:-1] + ['2027-01-01', '--strict']), 1)

    def test_output_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'existing.json'
            path.write_text('keep me')
            with contextlib.redirect_stderr(io.StringIO()):
                code = main([str(ROOT / 'examples/good.csv'), '--config', str(ROOT / 'examples/rules.json'), '--output', str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(path.read_text(), 'keep me')

    def test_module_entrypoint_json(self):
        proc = subprocess.run([sys.executable, '-m', 'catalog_guard', 'examples/good.csv', '--config',
                               'examples/rules.json', '--today', '2026-10-23', '--format', 'json'],
                              cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['records'], 2)

    def test_input_not_mutated(self):
        rows = [{'id': 'a', 'name': '  Demo  '}]
        before = json.dumps(rows)
        analyze(rows, {'id': 'id'})
        self.assertEqual(json.dumps(rows), before)


if __name__ == '__main__':
    unittest.main()
