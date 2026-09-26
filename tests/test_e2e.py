# tests/test_e2e.py
import unittest
import tempfile
import os
from tests.generate_test_data import create_sample_duplicates
from windedup.core.scanner import scan_directory
from windedup.core.rules import apply_keep_newest, apply_keep_oldest, apply_keep_shortest_path, apply_toss_all
from windedup.core.recycle import execute_deduplication, get_completely_discarded_groups

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

        self.assertEqual(len(groups), 2)
        total_files = sum(len(g.entries) for g in groups)
        self.assertEqual(total_files, 5)
        self.assertIn(100.0, progress_records)

        # 2. Test Keep Newest rule
        apply_keep_newest(groups)
        report_group = next(g for g in groups if "report" in g.filename)
        kept_report = next(e for e in report_group.entries if e.is_keep)
        self.assertIn("backup_report.txt", kept_report.path)

        # 3. Test completely discarded check (none discarded yet)
        discarded = get_completely_discarded_groups(groups)
        self.assertEqual(len(discarded), 0)

        # 4. Dedup execution (use_recycle_bin=False for unit test runner)
        deleted, freed, errs = execute_deduplication(groups, use_recycle_bin=False)
        self.assertEqual(errs, [])
        self.assertEqual(deleted, 3)
        self.assertTrue(freed > 0)
        self.assertTrue(os.path.exists(kept_report.path))

    def test_total_group_deletion_e2e(self):
        groups = scan_directory(self.test_dir)
        self.assertEqual(len(groups), 2)

        # Toss all copies of all groups
        apply_toss_all(groups)
        discarded = get_completely_discarded_groups(groups)
        self.assertEqual(len(discarded), 2)

        deleted, freed, errs = execute_deduplication(groups, use_recycle_bin=False)
        self.assertEqual(errs, [])
        self.assertEqual(deleted, 5)  # All 5 duplicate files removed
        self.assertTrue(freed > 0)

if __name__ == '__main__':
    unittest.main()
