# tests/test_scanner.py
import unittest
import tempfile
import os
import threading
from windedup.core.scanner import scan_directory

class TestScanner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = self.tmpdir.name

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_finds_duplicates_across_subfolders(self):
        sub1 = os.path.join(self.root, "sub1")
        sub2 = os.path.join(self.root, "sub2")
        os.makedirs(sub1)
        os.makedirs(sub2)

        content_dup = b"Duplicate file content 12345"
        content_uniq = b"Unique content"

        with open(os.path.join(self.root, "file_a.txt"), "wb") as f: f.write(content_dup)
        with open(os.path.join(sub1, "file_b.txt"), "wb") as f: f.write(content_dup)
        with open(os.path.join(sub2, "file_c.txt"), "wb") as f: f.write(content_dup)
        with open(os.path.join(sub1, "unique.txt"), "wb") as f: f.write(content_uniq)

        progresses = []
        def on_prog(p): progresses.append(p)

        groups = scan_directory(self.root, progress_callback=on_prog)

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(len(group.entries), 3)
        self.assertEqual(group.size, len(content_dup))
        self.assertTrue(any(p.percent == 100.0 for p in progresses))

    def test_cancellation(self):
        cancel_event = threading.Event()
        cancel_event.set()  # immediate cancel
        groups = scan_directory(self.root, cancel_event=cancel_event)
        self.assertEqual(groups, [])

    def test_no_duplicates_returns_empty(self):
        with open(os.path.join(self.root, "f1.txt"), "wb") as f: f.write(b"unique 1")
        with open(os.path.join(self.root, "f2.txt"), "wb") as f: f.write(b"unique 2")
        groups = scan_directory(self.root)
        self.assertEqual(groups, [])

if __name__ == '__main__':
    unittest.main()
