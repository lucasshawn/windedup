# Windedup - Windows Duplicate File Finder & Deduplicator Specification

**Date**: 2026-09-25  
**Status**: Approved  
**Target Repository**: `C:\Users\lucas\source\repos\windedup`  
**Runtime**: Python 3.14+ (Windows native `tkinter.ttk` + Windows Shell API via `ctypes`)

---

## 1. Executive Summary
**Windedup** is a Windows desktop application that scans a user-selected folder and all its subfolders to find identical duplicate files by content hash. Duplicates are organized into a hierarchical list view displaying file name, size, modification date, and all matching paths. The application enables rapid deduplication through smart bulk rules (Keep Newest, Keep Oldest, Keep Shortest Path, Prefer Folder) and manual per-item selection, safely sending discarded copies to the Windows Recycle Bin while strictly ensuring at least one original copy is preserved.

---

## 2. Requirements & User Stories

### 2.1 Functional Requirements
1. **Directory Selection & Traversal**:
   - The user can select any folder on local or network Windows drives via standard folder picker dialog or text input.
   - Traversal recursively discovers all files in subfolders, gracefully handling permission errors or unreadable paths.
2. **Two-Stage Discovery & Hashing Engine**:
   - Stage 1: Group files by byte size. Files with unique sizes are skipped immediately.
   - Stage 2: For files sharing identical sizes, read first 64 KB and calculate partial SHA-256 hash to eliminate size collisions.
   - Stage 3: For files with identical partial hashes, calculate full SHA-256 hash.
   - Zero-byte files: Handled consistently (grouped together if multiple exist).
3. **Progress Indication**:
   - During scanning and hashing, display an interactive progress dialog showing:
     - Current phase ("Enumerating files...", "Comparing file candidates: X%").
     - Numeric percentage (0% to 100%) and a graphical `ttk.Progressbar`.
     - Real-time count of files examined and candidate duplicates identified.
     - A functional "Cancel" button allowing safe abort of the scan at any point.
4. **Hierarchical Results Presentation**:
   - Display duplicate groups in a hierarchical `ttk.Treeview`:
     - **Parent Node**: File Name, Size (formatted: B, KB, MB, GB), Duplicate Count (`N copies`), Reclaimable Space, Hash summary.
     - **Child Nodes (Paths)**: Status badge (`[KEEP]` vs `[TOSS]`), Modified Date, and Full File Path.
     - All groups initially expanded for instant visibility.
5. **Deduplication Designation & Rules**:
   - Quick bulk selection rules via toolbar:
     - **Keep Newest**: For each group, marks the file with the most recent modification timestamp as `KEEP`, and all other copies as `TOSS`.
     - **Keep Oldest**: For each group, marks the file with the earliest modification timestamp as `KEEP`, and all others as `TOSS`.
     - **Keep Shortest Path**: Keeps the file with the shortest path string / shallowest folder depth.
     - **Prefer Folder**: Lets the user select a folder prefix; any duplicate inside that folder is marked `KEEP`, tossing outside copies.
   - Per-path manual toggle:
     - Double-click or Spacebar toggles a path between `KEEP` and `TOSS`.
     - Right-click context menu: "Keep this file (Toss others)", "Toss this file", "Open file in Explorer", "Properties".
   - Live reclaimable space tracker updating dynamically whenever selections change.
6. **Safe Execution**:
   - Primary action button: "Dedup Now".
   - Strict Safety Invariant: **Never allow all copies of a group to be tossed.** At least one copy must be marked `KEEP`. If violated, dedup is blocked with an alert.
   - Pre-deletion validation: Verifies each `KEEP` file still exists and is accessible before touching `TOSS` files.
   - Deletion mechanism: Default sends tossed files to the Windows Recycle Bin using `ctypes.windll.shell32.SHFileOperationW` (`FO_DELETE` with `FOF_ALLOWUNDO`). Optional checkbox allows permanent deletion if explicitly requested.
   - Detailed results dialog reporting total files removed, disk space freed, and any locked-file errors encountered.

---

## 3. Architecture & Module Design

### 3.1 Directory Structure
```
windedup/
├── .gitignore
├── README.md
├── main.py                     # Entry script running windedup.ui.app
├── windedup/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py           # FileEntry, DuplicateGroup, ScanProgress
│   │   ├── hasher.py           # 64KB partial hash & full SHA-256 hasher
│   │   ├── scanner.py          # Multithreaded folder scanner & progress callback
│   │   ├── rules.py            # Selection rules logic (newest, oldest, shortest, folder)
│   │   └── recycle.py          # Windows Shell API Recycle Bin wrapper via ctypes
│   └── ui/
│       ├── __init__.py
│       ├── app.py              # Main Tkinter application window & controller
│       ├── progress_dialog.py  # Modal percentage progress meter with Cancel button
│       └── tree_view.py        # Treeview widget with Keep/Toss badges and context menu
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_hasher.py
│   ├── test_scanner.py
│   ├── test_rules.py
│   └── test_recycle.py
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-09-25-windedup-design.md
```

### 3.2 Component Details

#### `core/models.py`
- `FileEntry`:
  - `path: str`
  - `size: int`
  - `mtime: float`
  - `hash: Optional[str]`
  - `is_keep: bool` (default: True for first item in group, False for others)
- `DuplicateGroup`:
  - `group_id: str`
  - `hash: str`
  - `size: int`
  - `entries: List[FileEntry]`
  - Property `keep_count -> int`
  - Property `toss_count -> int`
  - Property `reclaimable_bytes -> int`
- `ScanProgress`:
  - `phase: str` ("enumerating", "hashing")
  - `percent: float` (0.0 to 100.0)
  - `files_scanned: int`
  - `current_path: str`
  - `candidate_count: int`

#### `core/hasher.py`
- `CHUNK_SIZE = 65536` (64 KB).
- `compute_partial_hash(filepath: str) -> Optional[str]`: Reads up to 64 KB and computes SHA-256. Returns `None` on read/permission error.
- `compute_full_hash(filepath: str, progress_callback=None) -> Optional[str]`: Streams file in 64 KB blocks and computes full SHA-256.

#### `core/scanner.py`
- `scan_directory(root_dir: str, progress_cb, cancel_event) -> List[DuplicateGroup]`:
  1. Fast recursive walk using `os.scandir` to index `size -> [paths]`.
  2. Filter `size` groups where `len(paths) >= 2`.
  3. For matching sizes, compute partial 64 KB hash -> group by `(size, partial_hash)`.
  4. Filter groups where `len(paths) >= 2`.
  5. For matching partial hashes, compute full SHA-256 hash -> group by `(size, full_hash)`.
  6. Return list of `DuplicateGroup` objects containing 2 or more identical files.
  7. Regularly checks `cancel_event.is_set()` to cleanly exit.

#### `core/rules.py`
- `apply_keep_newest(groups: List[DuplicateGroup])`: For each group, the file with highest `mtime` has `is_keep=True`, others `is_keep=False`.
- `apply_keep_oldest(groups: List[DuplicateGroup])`: File with lowest `mtime` has `is_keep=True`, others `is_keep=False`.
- `apply_keep_shortest_path(groups: List[DuplicateGroup])`: File with shortest string length / least path segments has `is_keep=True`.
- `apply_prefer_folder(groups: List[DuplicateGroup], preferred_folder: str)`: File residing within `preferred_folder` is kept.

#### `core/recycle.py`
- Uses Windows `ctypes.windll.shell32.SHFileOperationW`.
- Struct `SHFILEOPSTRUCTW`:
  - `wFunc = FO_DELETE (0x0003)`
  - `fFlags = FOF_ALLOWUNDO (0x0040) | FOF_NOCONFIRMATION (0x0010) | FOF_SILENT (0x0004)`
  - `pFrom`: Double-null terminated wide string of paths.
- Provides fallback to `os.remove` only if the user explicitly unchecks the Recycle Bin option.
- Handles locked files gracefully by returning a list of `(filepath, error_message)` for any failures.

#### `ui/app.py` & `ui/tree_view.py`
- Built using `tkinter` and `tkinter.ttk` with Windows styling (`ttk.Style().theme_use('vista')` or `'winnative'`).
- Threaded scanning: UI thread remains responsive; background thread emits progress events to a `queue.Queue`, processed via `root.after(50, check_queue)`.
- Interactive `ttk.Treeview`:
  - Visual badges: `[KEEP]` formatted with distinct text styling; `[TOSS]` formatted with strike/distinct highlight.
  - Sorting support by clicking column headers.
  - Context menu for quick manual adjustments.

---

## 4. Safety Invariants & Error Handling
1. **Mandatory Keep Check**:
   Before deleting, `validate_groups_for_deletion(groups)` ensures:
   `for group in groups: assert group.keep_count >= 1`. If any group has 0 keeps, an alert prevents deletion.
2. **File Existence Validation**:
   Immediately prior to deleting a tossed file, the system checks `os.path.exists(keep_file)` for the corresponding kept file.
3. **Locked & Permission Denied Handling**:
   Permission errors during scan are logged and skipped without crashing the scan. Locked files during deletion are recorded in an error report presented to the user.

---

## 5. Verification Plan

### 5.1 Automated Unit Tests
- `pytest` or `unittest` running in Python 3.14:
  - `tests/test_models.py`: Model creation, keep/toss counting, reclaimable bytes calculation.
  - `tests/test_hasher.py`: Identical files, zero-byte files, small files (<64KB), large files (>1MB), collision simulation with same size but different content.
  - `tests/test_scanner.py`: Synthetic directory tree with nested folders, unique files, duplicates across subfolders, cancel token behavior.
  - `tests/test_rules.py`: Validates all 4 rules on known timestamps, path depths, and folder names.
  - `tests/test_recycle.py`: Validates delete list construction, double-null termination formatting, and safety checks.

### 5.2 Manual Verification
- Launch `python main.py`.
- Select a test folder containing duplicates.
- Observe % progress dialog smoothly updating during scan.
- Test quick rules (Newest, Oldest, Shortest).
- Toggle paths using double-click and right-click context menu.
- Verify safe deletion sends files to Windows Recycle Bin and updates Treeview.
