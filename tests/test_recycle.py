# tests/test_recycle.py
import unittest
import tempfile
import os
from windedup.core.models import FileEntry, DuplicateGroup
from windedup.core.recycle import validate_safety_invariants, execute_deduplication

class TestRecycle(unittest.TestCase):
    def test_prevents_deletion_when_no_keep_exists(self):
        f1 = FileEntry(path="a.txt", size=10, mtime=0, is_keep=False)
        f2 = FileEntry(path="b.txt", size=10, mtime=0, is_keep=False)
        group = DuplicateGroup(group_id="g1", hash="h", size=10, entries=[f1, f2])

        errors = validate_safety_invariants([group])
        self.assertTrue(len(errors) > 0)
        self.assertIn("has no designated file to KEEP", errors[0])

    def test_execute_deduplication_removes_toss_files(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            keep_path = os.path.join(tmp.name, "keep.txt")
            toss_path = os.path.join(tmp.name, "toss.txt")
            with open(keep_path, "wb") as f: f.write(b"content")
            with open(toss_path, "wb") as f: f.write(b"content")

            f_keep = FileEntry(path=keep_path, size=7, mtime=0, is_keep=True)
            f_toss = FileEntry(path=toss_path, size=7, mtime=0, is_keep=False)
            group = DuplicateGroup(group_id="g1", hash="h", size=7, entries=[f_keep, f_toss])

            count, freed, errors = execute_deduplication([group], use_recycle_bin=False)

            self.assertEqual(count, 1)
            self.assertEqual(freed, 7)
            self.assertEqual(len(errors), 0)
            self.assertTrue(os.path.exists(keep_path))
            self.assertFalse(os.path.exists(toss_path))
            self.assertEqual(len(group.entries), 1)
        finally:
            tmp.cleanup()

    def test_aborts_if_keep_file_is_missing(self):
        f_keep = FileEntry(path="nonexistent_keep.txt", size=10, mtime=0, is_keep=True)
        f_toss = FileEntry(path="some_toss.txt", size=10, mtime=0, is_keep=False)
        group = DuplicateGroup(group_id="g1", hash="h", size=10, entries=[f_keep, f_toss])

        count, freed, errors = execute_deduplication([group], use_recycle_bin=False)
        self.assertEqual(count, 0)
        self.assertTrue(len(errors) > 0)
        self.assertIn("None of the designated KEEP files exist", errors[0][1])

if __name__ == '__main__':
    unittest.main()
