# Windedup - File Menu and About Dialog Specification

**Date**: 2026-09-28  
**Status**: Approved  
**Target Repository**: `C:\Users\lucas\source\repos\windedup`  
**Branch**: `feature/about-menu`  
**Runtime**: Python 3.14+ (Windows native `tkinter.ttk`)

---

## 1. Executive Summary
This specification defines the addition of a native top-level **File Menu** and an **About Dialog** in the Windedup desktop application. The About dialog presents essential application provenance and metadata: Author name, Build Version, Build Date/Time, and Contact Email, alongside interactive utilities to email the author or copy the contact address to the Windows clipboard.

---

## 2. Requirements & User Stories

### 2.1 Top-Level File Menu
1. **Menu Bar Integration**:
   - The root window `WindedupApp` attaches a top-level menu bar (`tk.Menu`).
   - The menu bar contains a single "File" menu (`Alt+F` accelerator support).
   - "File" menu items:
     - `About Windedup...`: Opens the modal About Dialog.
     - Separator.
     - `Exit`: Gracefully closes and terminates the application (`self.destroy`).
2. **Visual Consistency**:
   - Conforms to standard Windows desktop styling, maintaining theme coherence across DPI scales.

### 2.2 About Dialog
1. **Metadata Displayed**:
   - **Application Name**: `Windedup`
   - **Application Description**: `Duplicate File Finder & Deduplicator for Windows`
   - **Author**: `Shawn Lucas`
   - **Build Version**: `1.1.0`
   - **Date / Time of Build**: Formatted build timestamp (`YYYY-MM-DD HH:MM:SS`) injected during build or fallback in development.
   - **Contact Author**: `lucas_shawn@hotmail.com`
2. **Visual Layout & Icon**:
   - Uses the application's transparent axe icon (`assets/icon.png`), displayed at 64x64 px.
   - Clean, modern layout matching the rest of the application (`Segoe UI` font family).
3. **Interactivity**:
   - **Clickable Email Link**: Clicking the email address triggers the default system mail client (`mailto:lucas_shawn@hotmail.com` via `webbrowser.open`).
   - **Copy Email Button**: Copies `lucas_shawn@hotmail.com` to the Windows clipboard and provides a momentary visual confirmation (`"Copied!"` for 2 seconds).
   - **Close Button**: Standard modal close button, plus `Escape` key and window close `[X]` support.
4. **Modal Behavior**:
   - Subclasses `tk.Toplevel`.
   - Centered over the parent `WindedupApp` window.
   - Transient to parent and sets modal grab (`grab_set()`).

### 2.3 Build Metadata Injection
1. **Approach**: Build-time injected metadata module via `Makefile`.
2. **Pipeline**:
   - The `Makefile`'s `build` target executes a Python script before invoking PyInstaller to generate `windedup/_build_info.py` containing `BUILD_TIMESTAMP = "<YYYY-MM-DD HH:MM:SS>"`.
   - `windedup/_build_info.py` is ignored in `.gitignore`.
   - `windedup/version.py` imports `BUILD_TIMESTAMP` from `windedup._build_info`. If missing (e.g. running uncompiled in dev mode), it returns `"Development Build"`.

---

## 3. Architecture & File Structure

```
windedup/
├── .gitignore                     # Ignores windedup/_build_info.py
├── Makefile                       # Updated 'build' target to inject build timestamp
├── windedup/
│   ├── version.py                 # Core metadata: VERSION, AUTHOR, CONTACT_EMAIL, get_build_timestamp()
│   ├── ui/
│   │   ├── about_dialog.py        # AboutDialog(tk.Toplevel) modal component
│   │   └── app.py                 # Attaches File menu and routes to AboutDialog
tests/
├── test_version.py                # Unit tests for metadata and build timestamp fallback/injection
└── test_about_dialog.py           # Unit/UI tests for AboutDialog instantiation & clipboard copy
```

---

## 4. Component Details

### 4.1 `windedup/version.py`
```python
import sys
from typing import Optional

APP_NAME = "Windedup"
APP_DESCRIPTION = "Duplicate File Finder & Deduplicator for Windows"
VERSION = "1.1.0"
AUTHOR = "Shawn Lucas"
CONTACT_EMAIL = "lucas_shawn@hotmail.com"

def get_build_timestamp() -> str:
    """Returns the injected build timestamp or fallback for development mode."""
    try:
        from windedup._build_info import BUILD_TIMESTAMP
        return BUILD_TIMESTAMP
    except ImportError:
        return "Development Build"
```

### 4.2 `windedup/ui/about_dialog.py`
- Inherits from `tk.Toplevel`.
- Configures title, geometry, transient parent, and grab.
- Renders:
  - Header: 64x64 icon + App Name + Description.
  - Body Frame: Label/Value pairs for Version, Author, Build Date/Time, and Contact Email.
  - Interactive controls: `Send Email` button/link and `Copy Email` button.
  - Footer: `Close` button.

### 4.3 `windedup/ui/app.py`
- In `_build_ui()`:
  - Constructs `tk.Menu(self)` and attaches `File` cascade.
  - Registers `_show_about_dialog()` callback which instantiates `AboutDialog(self)`.

### 4.4 `Makefile`
- Updates the `build` target:
  ```makefile
  build:
  	python -c "import datetime; open('windedup/_build_info.py', 'w').write(f'BUILD_TIMESTAMP = \"{datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\"\n')"
  	powershell -Command "Stop-Process -Name 'Windedup' -Force -ErrorAction SilentlyContinue"
  	pyinstaller Windedup.spec --noconfirm
  ```

---

## 5. Verification & Testing Plan

1. **Unit Testing (`tests/test_version.py`)**:
   - Verify `VERSION == "1.1.0"`.
   - Verify `AUTHOR == "Shawn Lucas"`.
   - Verify `CONTACT_EMAIL == "lucas_shawn@hotmail.com"`.
   - Verify `get_build_timestamp()` fallback behavior and explicit timestamp return when `_build_info` exists.
2. **UI Component Testing (`tests/test_about_dialog.py`)**:
   - Instantiation of `AboutDialog` with a hidden root window.
   - Verification of rendered labels.
   - Verification of `copy_to_clipboard` logic.
3. **Regression Suite**:
   - Execute `make test` (`python -m unittest discover tests -v`) and verify all 40+ tests pass.
4. **Binary Build Verification**:
   - Execute `make build` and verify `dist/Windedup.exe` compiles successfully with the embedded build timestamp.
