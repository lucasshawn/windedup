# tests/test_e2e.py
import unittest
import tempfile
import os
from tests.generate_test_data import create_sample_duplicates
from windedup.core.scanner import scan_directory
from windedup.core.rules import apply_keep_newest, apply_keep_oldest, apply_keep_shortest_path
from windedup.core.recycle import execute_deduplication, validate_safety_invariants

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.test_dir = os.path.join(self.tmp.name, "e2e_folder")
        create_sample_duplicates(self.test_dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_pipeline(self):
        # 1. Scan
        progress_records = []
        def on_prog(p):
            progress_records.append(p.percent)

        groups = scan_directory(self.test_dir, progress_callback=on_prog)

        # Expected 2 duplicate groups:
        # Group 1: report.txt (3 copies)
        # Group 2: graphic_asset.dat (2 copies)
        # Unique files (unique_file.txt, same_size_diff_content.txt) must NOT appear in duplicate groups
        self.assertEqual(len(groups), 2)
        total_files = sum(len(g.entries) for g in groups)
        self.assertEqual(total_files, 5)

        # Verify progress reached 100%
        self.assertIn(100.0, progress_records)

        # 2. Test Keep Newest rule
        apply_keep_newest(groups)
        report_group = next(g for g in groups if "report" in g.filename)
        # backup_report.txt has newest timestamp
        kept_report = next(e for e in report_group.entries if e.is_keep)
        self.assertIn("backup_report.txt", kept_report.path)

        # 3. Test Safety Invariant
        errors = validate_safety_invariants(groups)
        self.assertEqual(len(errors), 0)

        # 4. Dedup execution (use_recycle_bin=False for unit test runner)
        deleted, freed, errs = execute_deduplication(groups, use_recycle_bin=False)
        self.assertEqual(errs, [])
        self.assertEqual(deleted, 3)  # 2 from report group, 1 from graphic_asset group
        self.assertTrue(freed > 0)

        # 5. Check surviving files
        self.assertTrue(os.path.exists(kept_report.path))

if __name__ == '__main__':
    unittest.main()
