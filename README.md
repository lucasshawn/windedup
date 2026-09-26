# Windedup

**Windedup** is a Windows desktop application that traverses folders and subfolders to find identical duplicate files by content hash and empowers you to safely and quickly deduplicate them.

---

## Features

- **3-Stage Fast Hashing Pipeline**:
  1. *Size grouping*: Files with unique sizes are skipped instantly without reading contents.
  2. *Partial hash (64 KB)*: Rapidly tests the beginning of files to rule out false positives.
  3. *Full SHA-256 hash*: Byte-by-byte full checksum comparison for guaranteed identical matches.
- **Real-Time Progress Meter**:
  - Modal dialog showing **% Complete (0% – 100%)**, current phase, and file counts.
  - Responsive **Cancel** button to safely abort at any time.
- **Hierarchical Listview with Checkboxes**:
  - Interactive checkboxes on every file (`☑ TOSS` vs `☐ KEEP`) and tri-state checkboxes on parent group rows (`☑`, `☐`, `⊟`).
  - Toggle an entire duplicate group or individual files via click, double-click, or Spacebar.
  - Right-click context menus for quick actions.
- **Quick Filters & Bulk Selection**:
  - **Keep Newest**: Keeps the most recently modified copy.
  - **Keep Oldest**: Keeps the oldest copy.
  - **Keep Shortest Path**: Keeps the copy with the shallowest folder depth / shortest path string.
  - **Prefer Folder...**: Choose a folder to prioritize keeping files inside.
  - **Check All (Toss All)** & **Uncheck All (Keep All)**.
- **Total Group Removal**:
  - If you don't want any copies of a file, check the entire group to toss all copies. The confirmation dialog will explicitly note any groups being 100% removed.
- **Real-Time Deletion Progress Meter**:
  - Displays a live percentage bar, active file path being deleted, and dynamic reclaimed space counter during deduplication, with cancel support.
- **Custom Axe Icon**:
  - Embedded multi-resolution woodsman axe icon for the desktop executable and window titlebar.
- **Windows Recycle Bin Integration**:
  - Discarded files are moved directly to the Windows Recycle Bin using native Windows Shell APIs (`ctypes.windll.shell32.SHFileOperationW`) so they can be easily restored if needed.

---

## Requirements

- Windows 10 / 11 (x86_64)
- Python 3.10+ (tested on Python 3.14) to run from source, or run the standalone `.exe` directly.

---

## How to Run

### Option 1: Run the Standalone Windows Executable
A single-file portable `.exe` is built and located at:
```powershell
.\dist\Windedup.exe
```

### Option 2: Run via Python
```powershell
python main.py
```

---

## Building the Executable

To rebuild the standalone `.exe`:
```powershell
pyinstaller --noconsole --onefile --name "Windedup" main.py
```
The output executable will be placed in `dist/Windedup.exe`.

---

## Running the Tests

To run the automated test suite:

```powershell
python -m unittest discover tests -v
```
