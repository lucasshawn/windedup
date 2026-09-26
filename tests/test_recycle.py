# tests/test_recycle.py
import unittest
import tempfile
import os
from windedup.core.models import FileEntry, DuplicateGroup
from windedup.core.recycle import get_completely_discarded_groups, execute_deduplication

class TestRecycle(unittest.TestCase):
    def test_detects_completely_discarded_groups(self):
        f1 = FileEntry(path="a.txt", size=10, mtime=0, is_keep=False)
        f2 = FileEntry(path="b.txt", size=10, mtime=0, is_keep=False)
        group = DuplicateGroup(group_id="g1", hash="h", size=10, entries=[f1, f2])

        discarded = get_completely_discarded_groups([group])
        self.assertEqual(len(discarded), 1)
        self.assertEqual(discarded[0].group_id, "g1")

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

    def test_execute_deduplication_removes_all_copies_if_no_keep(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            p1 = os.path.join(tmp.name, "copy1.txt")
            p2 = os.path.join(tmp.name, "copy2.txt")
            with open(p1, "wb") as f: f.write(b"delete_all_copies")
            with open(p2, "wb") as f: f.write(b"delete_all_copies")

            f1 = FileEntry(path=p1, size=17, mtime=0, is_keep=False)
            f2 = FileEntry(path=p2, size=17, mtime=0, is_keep=False)
            group = DuplicateGroup(group_id="g1", hash="h", size=17, entries=[f1, f2])

            count, freed, errors = execute_deduplication([group], use_recycle_bin=False)

            self.assertEqual(count, 2)
            self.assertEqual(freed, 34)
            self.assertEqual(len(errors), 0)
            self.assertFalse(os.path.exists(p1))
            self.assertFalse(os.path.exists(p2))
            self.assertEqual(len(group.entries), 0)
        finally:
            tmp.cleanup()

    def test_aborts_if_designated_keep_file_is_missing(self):
        f_keep = FileEntry(path="nonexistent_keep.txt", size=10, mtime=0, is_keep=True)
        f_toss = FileEntry(path="some_toss.txt", size=10, mtime=0, is_keep=False)
        group = DuplicateGroup(group_id="g1", hash="h", size=10, entries=[f_keep, f_toss])

        count, freed, errors = execute_deduplication([group], use_recycle_bin=False)
        self.assertEqual(count, 0)
        self.assertTrue(len(errors) > 0)
        self.assertIn("None of the designated KEEP files exist", errors[0][1])

if __name__ == '__main__':
    unittest.main()
