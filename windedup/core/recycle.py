import os
import sys
import ctypes
from ctypes import wintypes
from typing import List, Tuple
from windedup.core.models import DuplicateGroup

# Windows SHFileOperation constants
FO_DELETE = 0x0003
FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400

class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.UINT),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]

def _send_to_recycle_bin(path: str) -> bool:
    """Sends a single file to the Windows Recycle Bin using SHFileOperationW."""
    if sys.platform != "win32":
        os.remove(path)
        return True

    # Windows SHFileOperation requires double-null terminated string
    abs_path = os.path.abspath(path)
    buffer = abs_path + "\0\0"

    fileop = SHFILEOPSTRUCTW()
    fileop.hwnd = 0
    fileop.wFunc = FO_DELETE
    fileop.pFrom = buffer
    fileop.pTo = None
    fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI

    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
    return (result == 0 and not fileop.fAnyOperationsAborted)

def validate_safety_invariants(groups: List[DuplicateGroup]) -> List[str]:
    """Ensures every duplicate group retains at least 1 KEEP file."""
    errors = []
    for g in groups:
        if g.keep_count == 0:
            errors.append(f"Group '{g.filename}' has no designated file to KEEP. At least 1 file must be kept.")
    return errors

def execute_deduplication(
    groups: List[DuplicateGroup],
    use_recycle_bin: bool = True
) -> Tuple[int, int, List[Tuple[str, str]]]:
    """
    Executes deletion of TOSS files across all groups.
    Returns (files_deleted, bytes_freed, error_list).
    """
    validation_errors = validate_safety_invariants(groups)
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    deleted_count = 0
    bytes_freed = 0
    errors: List[Tuple[str, str]] = []

    for g in groups:
        # Pre-check: Verify that at least one KEEP file is intact on disk
        keep_files = [e for e in g.entries if e.is_keep]
        intact_keep = any(os.path.exists(k.path) for k in keep_files)
        if not intact_keep:
            errors.append((g.filename, "None of the designated KEEP files exist on disk. Aborting deletion for this group."))
            continue

        surviving_entries = []
        for e in g.entries:
            if e.is_keep:
                surviving_entries.append(e)
            else:
                if not os.path.exists(e.path):
                    # Already gone
                    continue
                try:
                    if use_recycle_bin and sys.platform == "win32":
                        success = _send_to_recycle_bin(e.path)
                        if not success:
                            # Fallback if shell error occurred
                            os.remove(e.path)
                    else:
                        os.remove(e.path)
                    deleted_count += 1
                    bytes_freed += g.size
                except Exception as ex:
                    errors.append((e.path, str(ex)))
                    surviving_entries.append(e)

        g.entries = surviving_entries

    return deleted_count, bytes_freed, errors
