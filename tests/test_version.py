import sys
import types
import unittest
from unittest.mock import patch
import windedup.version as ver


class TestVersionMetadata(unittest.TestCase):
    def test_metadata_constants(self):
        self.assertEqual(ver.APP_NAME, "Windedup")
        self.assertEqual(ver.VERSION, "1.1.0")
        self.assertEqual(ver.AUTHOR, "PowerHouse PNW Development")
        self.assertEqual(ver.CONTACT_NAME, "PowerHouse PNW Development")
        self.assertEqual(ver.CONTACT_EMAIL, "powerhousepnw@gmail.com")
        self.assertIn("Duplicate File Finder", ver.APP_DESCRIPTION)

    def test_get_build_timestamp_fallback(self):
        # When _build_info is not present or unimported
        with patch.dict(sys.modules, {"windedup._build_info": None}):
            timestamp = ver.get_build_timestamp()
            self.assertIsInstance(timestamp, str)
            self.assertTrue(len(timestamp) > 0)
            self.assertEqual(timestamp, "Development Build")

    def test_get_build_timestamp_present(self):
        mock_mod = types.ModuleType("windedup._build_info")
        mock_mod.BUILD_TIMESTAMP = "2026-09-28 12:00:00"
        with patch.dict(sys.modules, {"windedup._build_info": mock_mod}):
            self.assertEqual(ver.get_build_timestamp(), "2026-09-28 12:00:00")

    def test_get_build_timestamp_missing_attribute(self):
        mock_mod = types.ModuleType("windedup._build_info")
        with patch.dict(sys.modules, {"windedup._build_info": mock_mod}):
            self.assertEqual(ver.get_build_timestamp(), "Development Build")


if __name__ == "__main__":
    unittest.main()
