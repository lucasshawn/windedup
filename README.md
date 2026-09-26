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
- **Hierarchical Listview (Treeview)**:
  - Parent groups display File Name, Size, Duplicate Count, and SHA-256 snippet.
  - Child rows display all file paths where the duplicate exists with `[ KEEP ]` or `[ TOSS ]` status badges, size, and date modified.
- **Quick Dedup Rules**:
  - **Keep Newest**: Keeps the most recently modified copy.
  - **Keep Oldest**: Keeps the oldest copy.
  - **Keep Shortest Path**: Keeps the copy with the shallowest folder depth / shortest path string.
  - **Prefer Folder...**: Choose a folder to prioritize keeping files inside.
- **Manual Granular Controls**:
  - Double-click or Spacebar on any path row to toggle Keep / Toss.
  - Right-click context menu: *Keep this file (Toss others)*, *Toss this file*, *Open in File Explorer*, *Open file*.
- **Zero-Loss Safety Guard**:
  - Enforces that at least one original copy of every duplicate group is kept. Total deletion of a group is strictly blocked.
- **Windows Recycle Bin Integration**:
  - Discarded files are moved directly to the Windows Recycle Bin using native Windows Shell APIs (`ctypes.windll.shell32.SHFileOperationW`) so they can be easily restored if needed.

---

## Requirements

- Windows 10 / 11
- Python 3.10+ (tested on Python 3.14)
- No third-party pip packages required (runs purely on Python Standard Library and native Windows APIs).

---

## How to Run

1. Clone or navigate to the repository:
   ```powershell
   cd C:\Users\lucas\source\repos\windedup
   ```

2. Run the application:
   ```powershell
   python main.py
   ```

---

## Running the Tests

To run the automated test suite:

```powershell
python -m unittest discover tests -v
```
