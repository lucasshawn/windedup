import unittest
import os
import sys
import logging
import threading
from windedup.core.logger import (
    get_log_file_path,
    setup_logging,
    log_and_show_exception,
    install_root_exception_handlers
)

class TestLogger(unittest.TestCase):
    def test_log_file_path(self):
        path = get_log_file_path()
        self.assertTrue(path.endswith("windedup.log"))
        self.assertTrue(os.path.isabs(path))

    def test_setup_logging(self):
        log_path = setup_logging()
        self.assertTrue(os.path.exists(os.path.dirname(log_path)))
        logging.info("Test log entry from TestLogger")

        # Confirm file exists and contains content
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Test log entry from TestLogger", content)

    def test_log_and_show_exception_no_dialog(self):
        try:
            raise ValueError("Test intentional crash exception")
        except ValueError:
            exc_type, exc_val, exc_tb = sys.exc_info()
            log_and_show_exception(
                exc_type,
                exc_val,
                exc_tb,
                context="Unit Test Context",
                show_dialog=False
            )

        log_path = get_log_file_path()
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Test intentional crash exception", content)
            self.assertIn("Unit Test Context", content)

    def test_install_root_exception_handlers(self):
        orig_sys_hook = sys.excepthook
        install_root_exception_handlers()
        self.assertNotEqual(sys.excepthook, orig_sys_hook)
        if hasattr(threading, "excepthook"):
            self.assertIsNotNone(threading.excepthook)

if __name__ == "__main__":
    unittest.main()
