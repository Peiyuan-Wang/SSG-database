"""Exercise the diagnostic entry point used to validate native distributions."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HAS_QT = any(importlib.util.find_spec(name) for name in ('PySide6', 'PyQt5'))


@unittest.skipUnless(HAS_QT, 'Optional Qt desktop dependencies are not installed')
class DesktopLaunchTests(unittest.TestCase):
    def launch(self, database, directory):
        report = directory / '检验 report.json'
        screenshot = directory / '窗口 preview.png'
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
        result = subprocess.run(
            [sys.executable, str(ROOT / 'run_desktop.py'), '--database', str(database),
             '--smoke-test', '--smoke-report', str(report),
             '--smoke-screenshot', str(screenshot)], cwd=directory, env=env,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        return result, report, screenshot

    def test_missing_database_exits_with_error_report_without_dialog(self):
        with tempfile.TemporaryDirectory(prefix='SSG 检验 ') as temporary:
            directory = Path(temporary)
            result, report, screenshot = self.launch(directory / 'missing.sqlite', directory)
            self.assertEqual(result.returncode, 1, result.stderr)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertFalse(data['ok'])
            self.assertIn('missing.sqlite', data['error'])
            self.assertFalse(screenshot.exists())

    def test_launch_proves_real_queries_and_saves_rendered_window(self):
        database = Path(os.environ.get('SSG_TEST_DATABASE',ROOT / 'output/retrieval/SSGclassify.sqlite')).resolve()
        if not database.is_file():
            self.skipTest('Full database is a separate release asset')
        with tempfile.TemporaryDirectory(prefix='SSG 检验 ') as temporary:
            result, report, screenshot = self.launch(database, Path(temporary))
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertTrue(data['ok'])
            self.assertEqual(data['classes'], 67475)
            self.assertEqual(data['parents'], 230)
            self.assertEqual(data['formulas'], 67475)
            self.assertEqual(data['specialized_c7'], ['P1.5.1'])
            self.assertEqual(data['detail'], 'N143.5.2')
            self.assertTrue(data['vector_valid'])
            self.assertEqual(screenshot.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')


if __name__ == '__main__':
    unittest.main()
