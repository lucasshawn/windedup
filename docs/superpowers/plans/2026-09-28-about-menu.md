# File Menu and About Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a top-level File Menu with "About Windedup..." and "Exit" to the UI, displaying an About dialog containing Author, Build Date/Time, Version, and interactive Contact Author utilities.

**Architecture:** A standalone `windedup/version.py` module defines core application metadata and dynamically reads build timestamps injected by the `Makefile` (with fallback for dev). A modal `AboutDialog` in `windedup/ui/about_dialog.py` presents this metadata alongside the axe icon and contact actions. `WindedupApp` attaches a native `tk.Menu` menubar to open the dialog.

**Tech Stack:** Python 3.14+, Tkinter (`tkinter.ttk`), `unittest`, PyInstaller, `make`.

## Global Constraints
- Target Repository: `C:\Users\lucas\source\repos\windedup`
- Branch: `feature/about-menu`
- Author Name: `Shawn Lucas` (exact)
- Contact Email: `lucas_shawn@hotmail.com` (exact)
- Build Version: `1.1.0` (exact)
- Standard library Python only (no external pip dependencies for core app logic).

---

### Task 1: Version Metadata & Build Timestamp Module

**Files:**
- Create: `windedup/version.py`
- Test: `tests/test_version.py`

**Interfaces:**
- Consumes: `windedup._build_info.BUILD_TIMESTAMP` (optional, injected at build time)
- Produces: `VERSION: str`, `AUTHOR: str`, `CONTACT_EMAIL: str`, `APP_NAME: str`, `APP_DESCRIPTION: str`, `get_build_timestamp() -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_version.py
import unittest
import sys
from unittest.mock import patch
import windedup.version as ver

class TestVersionMetadata(unittest.TestCase):
    def test_metadata_constants(self):
        self.assertEqual(ver.APP_NAME, "Windedup")
        self.assertEqual(ver.VERSION, "1.1.0")
        self.assertEqual(ver.AUTHOR, "Shawn Lucas")
        self.assertEqual(ver.CONTACT_EMAIL, "lucas_shawn@hotmail.com")
        self.assertIn("Duplicate File Finder", ver.APP_DESCRIPTION)

    def test_get_build_timestamp_fallback(self):
        # When _build_info is not present or unimported
        with patch.dict(sys.modules, {"windedup._build_info": None}):
            timestamp = ver.get_build_timestamp()
            self.assertIsInstance(timestamp, str)
            self.assertTrue(len(timestamp) > 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_version.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'windedup.version'`

- [ ] **Step 3: Write minimal implementation**

```python
# windedup/version.py
"""
Windedup application metadata and build information.
"""

APP_NAME = "Windedup"
APP_DESCRIPTION = "Duplicate File Finder & Deduplicator for Windows"
VERSION = "1.1.0"
AUTHOR = "Shawn Lucas"
CONTACT_EMAIL = "lucas_shawn@hotmail.com"


def get_build_timestamp() -> str:
    """
    Returns the build timestamp string.
    If generated during build by Makefile, returns the value in windedup._build_info.
    Otherwise returns 'Development Build'.
    """
    try:
        from windedup._build_info import BUILD_TIMESTAMP  # type: ignore
        return BUILD_TIMESTAMP
    except (ImportError, ModuleNotFoundError, AttributeError):
        return "Development Build"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_version.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add windedup/version.py tests/test_version.py
git commit -m "feat: add version metadata and build timestamp module"
```

---

### Task 2: Makefile Build Injection & .gitignore

**Files:**
- Modify: `.gitignore`
- Modify: `Makefile`
- Test: `tests/test_version.py` (add test for injected timestamp)

**Interfaces:**
- Consumes: Python standard library `datetime`
- Produces: `windedup/_build_info.py` generated on `make build`

- [ ] **Step 1: Write test for injected build timestamp**

In `tests/test_version.py`, add:
```python
    def test_get_build_timestamp_with_injected_info(self):
        import types
        mock_mod = types.ModuleType("windedup._build_info")
        mock_mod.BUILD_TIMESTAMP = "2026-09-28 12:00:00"
        with patch.dict(sys.modules, {"windedup._build_info": mock_mod}):
            self.assertEqual(ver.get_build_timestamp(), "2026-09-28 12:00:00")
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m unittest tests/test_version.py -v`
Expected: PASS

- [ ] **Step 3: Update `.gitignore` and `Makefile`**

In `.gitignore`, add:
```gitignore
windedup/_build_info.py
```

In `Makefile`, update `build` target:
```makefile
build:
	python -c "import datetime; open('windedup/_build_info.py', 'w').write(f'BUILD_TIMESTAMP = \"{datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\"\n')"
	powershell -Command "Stop-Process -Name 'Windedup' -Force -ErrorAction SilentlyContinue"
	pyinstaller Windedup.spec --noconfirm
```

- [ ] **Step 4: Verify syntax and dry-run timestamp generation**

Run: `python -c "import datetime; open('windedup/_build_info.py', 'w').write(f'BUILD_TIMESTAMP = \"{datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\"\n')"`
Verify `windedup/_build_info.py` exists, contains `BUILD_TIMESTAMP`, and `git status` shows `.gitignore` correctly ignores it. Then delete the test `_build_info.py`.

- [ ] **Step 5: Commit**

```bash
git add .gitignore Makefile tests/test_version.py
git commit -m "build: inject build timestamp in Makefile and ignore _build_info.py"
```

---

### Task 3: About Dialog Component

**Files:**
- Create: `windedup/ui/about_dialog.py`
- Test: `tests/test_about_dialog.py`

**Interfaces:**
- Consumes: `windedup.version` (APP_NAME, APP_DESCRIPTION, VERSION, AUTHOR, CONTACT_EMAIL, get_build_timestamp), `assets/icon.png`
- Produces: `AboutDialog(tk.Toplevel)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_about_dialog.py
import unittest
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
        self.assertEqual(dialog.title(), "About Windedup")
        self.assertEqual(dialog.author_label.cget("text"), ver.AUTHOR)
        self.assertEqual(dialog.version_label.cget("text"), ver.VERSION)
        self.assertEqual(dialog.email_label.cget("text"), ver.CONTACT_EMAIL)
        
        # Test copy to clipboard
        dialog._copy_email()
        clipboard_content = self.root.clipboard_get()
        self.assertEqual(clipboard_content, ver.CONTACT_EMAIL)
        
        dialog.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_about_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'windedup.ui.about_dialog'`

- [ ] **Step 3: Write minimal implementation**

```python
# windedup/ui/about_dialog.py
import tkinter as tk
from tkinter import ttk
import os
import sys
import webbrowser

from windedup.version import (
    APP_NAME,
    APP_DESCRIPTION,
    VERSION,
    AUTHOR,
    CONTACT_EMAIL,
    get_build_timestamp,
)


class AboutDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title(f"About {APP_NAME}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._load_icon()
        self._build_ui()
        self._center_window(parent)

        self.bind("<Escape>", lambda e: self.destroy())

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ico_path = os.path.join(base_dir, "assets", "icon.ico")
        png_path = os.path.join(base_dir, "assets", "icon.png")

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        self._header_img = None
        if os.path.exists(png_path):
            try:
                full_img = tk.PhotoImage(file=png_path)
                # Subsample 512x512 down to approx 64x64 (divide by 8)
                self._header_img = full_img.subsample(8, 8)
            except Exception:
                pass

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=(24, 20))
        main_frame.pack(fill="both", expand=True)

        # Header Frame: Icon + Title + Subtitle
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 16))

        if self._header_img:
            lbl_icon = ttk.Label(header_frame, image=self._header_img)
            lbl_icon.pack(side="left", padx=(0, 16))

        header_text = ttk.Frame(header_frame)
        header_text.pack(side="left", fill="both", expand=True)

        lbl_title = ttk.Label(header_text, text=APP_NAME, font=("Segoe UI", 16, "bold"))
        lbl_title.pack(anchor="w")

        lbl_desc = ttk.Label(
            header_text,
            text=APP_DESCRIPTION,
            font=("Segoe UI", 9),
            foreground="#555555",
            wraplength=280
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # Metadata Card
        card = ttk.LabelFrame(main_frame, text=" Build & Provenance ", padding=(16, 12))
        card.pack(fill="x", pady=(0, 16))

        rows = [
            ("Version:", VERSION),
            ("Build Date / Time:", get_build_timestamp()),
            ("Author:", AUTHOR),
            ("Contact:", CONTACT_EMAIL),
        ]

        for i, (label_text, val_text) in enumerate(rows):
            ttk.Label(card, text=label_text, font=("Segoe UI", 9, "bold")).grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=4
            )
            val_lbl = ttk.Label(card, text=val_text, font=("Segoe UI", 9))
            val_lbl.grid(row=i, column=1, sticky="w", pady=4)

            if label_text == "Version:":
                self.version_label = val_lbl
            elif label_text == "Author:":
                self.author_label = val_lbl
            elif label_text == "Build Date / Time:":
                self.build_time_label = val_lbl
            elif label_text == "Contact:":
                self.email_label = val_lbl
                val_lbl.configure(foreground="#0066cc", cursor="hand2")
                val_lbl.bind("<Button-1>", lambda e: self._send_email())

        # Email Actions Frame
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(0, 16))

        self.btn_copy = ttk.Button(action_frame, text="Copy Email", command=self._copy_email)
        self.btn_copy.pack(side="left", padx=(0, 8))

        btn_mail = ttk.Button(action_frame, text="Send Email", command=self._send_email)
        btn_mail.pack(side="left")

        # Bottom Button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x")
        btn_close = ttk.Button(bottom_frame, text="Close", command=self.destroy, width=10)
        btn_close.pack(side="right")
        btn_close.focus_set()

    def _copy_email(self):
        self.clipboard_clear()
        self.clipboard_append(CONTACT_EMAIL)
        self.update()
        self.btn_copy.configure(text="Copied!")
        self.after(2000, lambda: self.btn_copy.configure(text="Copy Email"))

    def _send_email(self):
        webbrowser.open(f"mailto:{CONTACT_EMAIL}")

    def _center_window(self, parent: tk.Tk):
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 440)
        h = max(self.winfo_reqheight(), 340)

        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()

        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_about_dialog.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add windedup/ui/about_dialog.py tests/test_about_dialog.py
git commit -m "feat: implement AboutDialog modal with author, version, build time, and email actions"
```

---

### Task 4: File Menu Integration in Main App

**Files:**
- Modify: `windedup/ui/app.py`
- Modify: `tests/test_e2e.py`

**Interfaces:**
- Consumes: `windedup.ui.about_dialog.AboutDialog`
- Produces: Top-level native menubar `File -> [About Windedup..., Separator, Exit]` on `WindedupApp`

- [ ] **Step 1: Write integration test verifying menu configuration**

In `tests/test_e2e.py`, add a test:
```python
    def test_file_menu_attached(self):
        from windedup.ui.app import WindedupApp
        app = WindedupApp()
        app.withdraw()
        try:
            menu_bar = app.cget("menu")
            self.assertTrue(menu_bar)
            # Find the File cascade menu
            menu_obj = app.nametowidget(menu_bar)
            file_menu = menu_obj.nametowidget(menu_obj.entrycget(1, "menu"))
            # Check entry labels
            labels = [file_menu.entrycget(i, "label") for i in range(file_menu.index("end") + 1) if file_menu.type(i) != "separator"]
            self.assertIn("About Windedup...", labels)
            self.assertIn("Exit", labels)
        finally:
            app.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_e2e.py -v`
Expected: FAIL (no menu configured on `app`)

- [ ] **Step 3: Implement Menu Bar in `windedup/ui/app.py`**

In `windedup/ui/app.py`:
1. Import `AboutDialog`:
   ```python
   from windedup.ui.about_dialog import AboutDialog
   ```
2. In `_build_ui()`:
   ```python
   # 0. Top Menu Bar
   menubar = tk.Menu(self)
   file_menu = tk.Menu(menubar, tearoff=0)
   file_menu.add_command(label="About Windedup...", command=self._show_about_dialog)
   file_menu.add_separator()
   file_menu.add_command(label="Exit", command=self.destroy)
   menubar.add_cascade(label="File", menu=file_menu)
   self.config(menu=menubar)
   ```
3. Add callback method:
   ```python
   def _show_about_dialog(self):
       AboutDialog(self)
   ```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_e2e.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add windedup/ui/app.py tests/test_e2e.py
git commit -m "feat: attach File menu with About Windedup and Exit actions"
```

---

### Task 5: Build Executable & Full Verification

**Files:**
- Execute: `make test`
- Execute: `make build`
- Verify: `dist/Windedup.exe`

- [ ] **Step 1: Run full test suite**

Run: `python -m unittest discover tests -v`
Expected: All 40+ tests pass with 0 failures and 0 errors.

- [ ] **Step 2: Build production executable via Makefile**

Run: `make build`
Expected: Injects `_build_info.py`, terminates old running instances, compiles `dist/Windedup.exe`.

- [ ] **Step 3: Push feature branch to remote**

```bash
git push -u origin feature/about-menu
```

- [ ] **Step 4: Confirm complete deliverable**
