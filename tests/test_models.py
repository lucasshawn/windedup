# tests/test_models.py
import unittest
from windedup.core.models import FileEntry, DuplicateGroup, ScanProgress

class TestModels(unittest.TestCase):
    def test_file_entry_defaults(self):
        entry = FileEntry(path=r"C:\test\a.txt", size=1024, mtime=1700000000.0)
        self.assertEqual(entry.path, r"C:\test\a.txt")
        self.assertEqual(entry.size, 1024)
        self.assertEqual(entry.mtime, 1700000000.0)
        self.assertIsNone(entry.hash)
        self.assertTrue(entry.is_keep)

    def test_duplicate_group_properties(self):
        f1 = FileEntry(path=r"C:\test\copy1.txt", size=500, mtime=1700000000.0, is_keep=True)
        f2 = FileEntry(path=r"C:\test\copy2.txt", size=500, mtime=1700001000.0, is_keep=False)
        f3 = FileEntry(path=r"C:\test\sub\copy3.txt", size=500, mtime=1700002000.0, is_keep=False)
        group = DuplicateGroup(group_id="g1", hash="abc123hash", size=500, entries=[f1, f2, f3])

        self.assertEqual(group.keep_count, 1)
        self.assertEqual(group.toss_count, 2)
        self.assertEqual(group.reclaimable_bytes, 1000)
        self.assertEqual(group.filename, "copy1.txt")

    def test_scan_progress(self):
        prog = ScanProgress(phase="hashing", percent=45.5, files_scanned=120, current_path=r"C:\test\b.txt", candidate_count=10)
        self.assertEqual(prog.percent, 45.5)
        self.assertEqual(prog.phase, "hashing")

if __name__ == '__main__':
    unittest.main()
