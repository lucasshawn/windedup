# tests/test_hasher.py
import unittest
import tempfile
import os
import hashlib
from windedup.core.hasher import compute_partial_hash, compute_full_hash

class TestHasher(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_identical_files_produce_same_hash(self):
        content = b"A" * 100000
        p1 = os.path.join(self.tmpdir.name, "f1.bin")
        p2 = os.path.join(self.tmpdir.name, "f2.bin")
        with open(p1, "wb") as f: f.write(content)
        with open(p2, "wb") as f: f.write(content)

        part1 = compute_partial_hash(p1)
        part2 = compute_partial_hash(p2)
        full1 = compute_full_hash(p1)
        full2 = compute_full_hash(p2)

        self.assertIsNotNone(part1)
        self.assertEqual(part1, part2)
        self.assertIsNotNone(full1)
        self.assertEqual(full1, full2)
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(full1, expected)

    def test_same_size_different_content(self):
        p1 = os.path.join(self.tmpdir.name, "f1.bin")
        p2 = os.path.join(self.tmpdir.name, "f2.bin")
        with open(p1, "wb") as f: f.write(b"A" * 1000)
        with open(p2, "wb") as f: f.write(b"B" * 1000)

        self.assertNotEqual(compute_partial_hash(p1), compute_partial_hash(p2))
        self.assertNotEqual(compute_full_hash(p1), compute_full_hash(p2))

    def test_same_prefix_different_tail(self):
        # 64KB identical prefix, differing tail
        prefix = b"Z" * 65536
        p1 = os.path.join(self.tmpdir.name, "f1.bin")
        p2 = os.path.join(self.tmpdir.name, "f2.bin")
        with open(p1, "wb") as f: f.write(prefix + b"1")
        with open(p2, "wb") as f: f.write(prefix + b"2")

        # Partial hash matches (first 64KB)
        self.assertEqual(compute_partial_hash(p1), compute_partial_hash(p2))
        # Full hash differs!
        self.assertNotEqual(compute_full_hash(p1), compute_full_hash(p2))

    def test_nonexistent_or_unreadable_file_returns_none(self):
        self.assertIsNone(compute_partial_hash("nonexistent_file_path_123.tmp"))
        self.assertIsNone(compute_full_hash("nonexistent_file_path_123.tmp"))

if __name__ == '__main__':
    unittest.main()
