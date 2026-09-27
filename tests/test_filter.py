import unittest
from windedup.core.models import FileEntry, DuplicateGroup
from windedup.core.filter import (
    parse_masks,
    match_single_mask,
    filter_file_entry,
    filter_duplicate_groups
)

class TestFilter(unittest.TestCase):
    def test_parse_masks(self):
        self.assertEqual(parse_masks(""), [])
        self.assertEqual(parse_masks("   ; ;  "), [])
        self.assertEqual(
            parse_masks("*.jpg; *.png ; docs\\* ; ; *temp*"),
            ["*.jpg", "*.png", "docs\\*", "*temp*"]
        )

    def test_match_single_mask_extensions(self):
        path = r"C:\Users\lucas\Pictures\vacation.JPG"
        self.assertTrue(match_single_mask(path, "*.jpg"))
        self.assertTrue(match_single_mask(path, "*.JPG"))
        self.assertFalse(match_single_mask(path, "*.png"))

    def test_match_single_mask_paths(self):
        path = r"C:\projects\app\node_modules\pkg\index.js"
        self.assertTrue(match_single_mask(path, r"node_modules\*"))
        self.assertTrue(match_single_mask(path, r"node_modules/*"))
        self.assertTrue(match_single_mask(path, "node_modules"))
        self.assertFalse(match_single_mask(path, r"src\*"))

    def test_filter_file_entry(self):
        e1 = FileEntry(path=r"C:\data\docs\report.pdf", size=100)
        e2 = FileEntry(path=r"C:\data\temp\cache.tmp", size=100)

        # Include only
        self.assertTrue(filter_file_entry(e1, ["*.pdf"], []))
        self.assertFalse(filter_file_entry(e2, ["*.pdf"], []))

        # Exclude only
        self.assertTrue(filter_file_entry(e1, [], ["*temp*", "*.tmp"]))
        self.assertFalse(filter_file_entry(e2, [], ["*temp*", "*.tmp"]))

        # Include and exclude combined
        e3 = FileEntry(path=r"C:\data\temp\report.pdf", size=100)
        # Matches include *.pdf, but also matches exclude *temp* -> must be rejected
        self.assertFalse(filter_file_entry(e3, ["*.pdf"], ["*temp*"]))

    def test_filter_duplicate_groups(self):
        e1 = FileEntry(path=r"C:\docs\doc1.pdf", size=500, is_keep=True)
        e2 = FileEntry(path=r"C:\backup\doc1.pdf", size=500, is_keep=False)
        e3 = FileEntry(path=r"C:\temp\doc1.pdf", size=500, is_keep=False)
        group1 = DuplicateGroup(group_id="g1", hash="hash1", size=500, entries=[e1, e2, e3])

        e4 = FileEntry(path=r"C:\data\img.png", size=200, is_keep=True)
        e5 = FileEntry(path=r"C:\temp\img.png", size=200, is_keep=False)
        group2 = DuplicateGroup(group_id="g2", hash="hash2", size=200, entries=[e4, e5])

        groups = [group1, group2]

        # Case 1: Exclude *temp*
        # group1 loses e3, but retains e1 and e2 (>= 2) -> kept!
        # group2 loses e5, retains only e4 (< 2) -> hidden!
        filtered = filter_duplicate_groups(groups, [], ["*temp*"])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].group_id, "g1")
        self.assertEqual(len(filtered[0].entries), 2)
        self.assertEqual(filtered[0].entries[0].path, r"C:\docs\doc1.pdf")
        self.assertEqual(filtered[0].entries[1].path, r"C:\backup\doc1.pdf")

        # Case 2: Include only *.png
        # group1 has zero matches (< 2) -> hidden!
        # group2 has 2 matches (>= 2) -> kept!
        filtered_png = filter_duplicate_groups(groups, ["*.png"], [])
        self.assertEqual(len(filtered_png), 1)
        self.assertEqual(filtered_png[0].group_id, "g2")
        self.assertEqual(len(filtered_png[0].entries), 2)

        # Case 3: Empty filters
        self.assertEqual(len(filter_duplicate_groups(groups, [], [])), 2)

    def test_match_single_mask_precision(self):
        path = r"C:\Users\lucas\Projects\temp\file.txt"
        # Single letters should NOT match drive or parent folders
        self.assertFalse(match_single_mask(path, "c"))
        self.assertFalse(match_single_mask(path, "u"))
        # Partial substring should not match full folder name
        self.assertFalse(match_single_mask(path, "proj"))
        # Whole folder component should match
        self.assertTrue(match_single_mask(path, "temp"))
        self.assertTrue(match_single_mask(path, "Projects"))

    def test_filter_promotes_surviving_entry_to_keep_when_keep_file_is_excluded(self):
        e1 = FileEntry(path=r"C:\Photos\pic1.jpg", size=1000, is_keep=True)
        e2 = FileEntry(path=r"C:\Backup\pic1.jpg", size=1000, is_keep=False)
        e3 = FileEntry(path=r"C:\Temp\pic1.jpg", size=1000, is_keep=False)
        group = DuplicateGroup(group_id="g1", hash="h1", size=1000, entries=[e1, e2, e3])

        # Exclude Photos -> e1 is removed.
        # e2 and e3 survive, and e2 must be automatically promoted to KEEP so both are not tossed!
        filtered = filter_duplicate_groups([group], [], ["Photos"])
        self.assertEqual(len(filtered), 1)
        entries = filtered[0].entries
        self.assertEqual(len(entries), 2)
        # Verify at least one surviving entry is KEEP
        self.assertTrue(any(e.is_keep for e in entries))
        self.assertTrue(entries[0].is_keep)
        self.assertFalse(entries[1].is_keep)

if __name__ == "__main__":
    unittest.main()
