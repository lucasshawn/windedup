import unittest
import os
import sys
from windedup.core.logger import (
    get_crash_marker_path,
    write_crash_marker,
    has_previous_crash,
    clear_previous_crash,
    get_crash_report_text,
    log_and_show_exception
)

class TestCrashReporter(unittest.TestCase):
    def setUp(self):
        clear_previous_crash()

    def tearDown(self):
        clear_previous_crash()

    def test_write_and_read_crash_marker(self):
        try:
            raise RuntimeError("Simulated crash for testing")
        except RuntimeError:
            exc_type, exc_val, exc_tb = sys.exc_info()
            write_crash_marker(exc_type, exc_val, exc_tb, context="Test Runner")

        info = has_previous_crash()
        self.assertIsNotNone(info)
        self.assertEqual(info["error_type"], "RuntimeError")
        self.assertEqual(info["error_message"], "Simulated crash for testing")
        self.assertEqual(info["context"], "Test Runner")
        self.assertIn("Traceback", info["traceback"])

        report = get_crash_report_text(info)
        self.assertIn("powerhousepnw@gmail.com", report)
        self.assertIn("PowerHouse PNW Development", report)
        self.assertIn("RuntimeError", report)

    def test_clear_crash_marker(self):
        try:
            raise KeyError("Missing key")
        except KeyError:
            exc_type, exc_val, exc_tb = sys.exc_info()
            write_crash_marker(exc_type, exc_val, exc_tb, context="Clear Test")

        self.assertIsNotNone(has_previous_crash())
        clear_previous_crash()
        self.assertIsNone(has_previous_crash())

    def test_log_and_show_exception_creates_marker(self):
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            exc_type, exc_val, exc_tb = sys.exc_info()
            log_and_show_exception(
                exc_type,
                exc_val,
                exc_tb,
                context="Math Operation",
                show_dialog=False
            )

        info = has_previous_crash()
        self.assertIsNotNone(info)
        self.assertEqual(info["error_type"], "ZeroDivisionError")
        self.assertEqual(info["context"], "Math Operation")

    def test_consume_previous_crash(self):
        from windedup.core.logger import consume_previous_crash
        try:
            raise ValueError("Consume test")
        except ValueError:
            exc_type, exc_val, exc_tb = sys.exc_info()
            write_crash_marker(exc_type, exc_val, exc_tb, context="Consume Context")

        self.assertIsNotNone(has_previous_crash())
        info = consume_previous_crash()
        self.assertIsNotNone(info)
        self.assertEqual(info["error_message"], "Consume test")
        # Ensure it was cleared from disk
        self.assertIsNone(has_previous_crash())

if __name__ == "__main__":
    unittest.main()
