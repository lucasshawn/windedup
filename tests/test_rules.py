# tests/test_rules.py
import unittest
from windedup.core.models import FileEntry, DuplicateGroup
from windedup.core.rules import (
    apply_keep_newest,
    apply_keep_oldest,
    apply_keep_shortest_path,
    apply_prefer_folder
)

class TestRules(unittest.TestCase):
    def setUp(self):
        self.f_old = FileEntry(path=r"C:\dir\very\long\nested\old.txt", size=100, mtime=1000.0)
        self.f_mid = FileEntry(path=r"C:\dir\mid.txt", size=100, mtime=2000.0)
        self.f_new = FileEntry(path=r"C:\preferred\dir\new.txt", size=100, mtime=3000.0)
        self.group = DuplicateGroup(group_id="g1", hash="h1", size=100, entries=[self.f_old, self.f_mid, self.f_new])

    def test_keep_newest(self):
        apply_keep_newest([self.group])
        self.assertTrue(self.f_new.is_keep)
        self.assertFalse(self.f_mid.is_keep)
        self.assertFalse(self.f_old.is_keep)

    def test_keep_oldest(self):
        apply_keep_oldest([self.group])
        self.assertTrue(self.f_old.is_keep)
        self.assertFalse(self.f_mid.is_keep)
        self.assertFalse(self.f_new.is_keep)

    def test_keep_shortest_path(self):
        apply_keep_shortest_path([self.group])
        self.assertTrue(self.f_mid.is_keep)  # C:\dir\mid.txt is shortest
        self.assertFalse(self.f_old.is_keep)
        self.assertFalse(self.f_new.is_keep)

    def test_prefer_folder(self):
        apply_prefer_folder([self.group], r"C:\preferred")
        self.assertTrue(self.f_new.is_keep)
        self.assertFalse(self.f_mid.is_keep)
        self.assertFalse(self.f_old.is_keep)

if __name__ == '__main__':
    unittest.main()
