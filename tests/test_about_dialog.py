import unittest
from unittest.mock import patch
import tkinter as tk
from windedup.ui.about_dialog import AboutDialog
import windedup.version as ver


class TestAboutDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_about_dialog_creation_and_attributes(self):
        dialog = AboutDialog(self.root)
        self.assertEqual(dialog.title(), f"About {ver.APP_NAME}")
        self.assertEqual(dialog.author_label.cget("text"), ver.AUTHOR)
        self.assertEqual(dialog.contact_name_label.cget("text"), ver.CONTACT_NAME)
        self.assertEqual(dialog.version_label.cget("text"), ver.VERSION)
        self.assertEqual(dialog.build_time_label.cget("text"), ver.get_build_timestamp())
        self.assertEqual(dialog.email_label.cget("text"), ver.CONTACT_EMAIL)
        self.assertIsNotNone(dialog.banner_label)

        # Test copy to clipboard
        dialog._copy_email()
        clipboard_content = self.root.clipboard_get()
        self.assertEqual(clipboard_content, ver.CONTACT_EMAIL)
        self.assertEqual(dialog.btn_copy.cget("text"), "Copied!")

        dialog.destroy()

    @patch("webbrowser.open")
    def test_about_dialog_send_email(self, mock_browser_open):
        dialog = AboutDialog(self.root)
        dialog._send_email()
        mock_browser_open.assert_called_once_with(f"mailto:{ver.CONTACT_EMAIL}")
        dialog.destroy()


if __name__ == "__main__":
    unittest.main()
