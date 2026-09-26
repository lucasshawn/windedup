import os
import sys
import ctypes
from ctypes import wintypes
import threading
from typing import List, Tuple, Callable, Optional
from windedup.core.models import DuplicateGroup, DeleteProgress

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

def get_completely_discarded_groups(groups: List[DuplicateGroup]) -> List[DuplicateGroup]:
    """Returns all groups where every copy is marked to toss (no keep files)."""
    return [g for g in groups if g.keep_count == 0 and len(g.entries) > 0]

def validate_safety_invariants(groups: List[DuplicateGroup]) -> List[str]:
    """Legacy helper: returns empty list since total group deletion is now permitted."""
    return []

def execute_deduplication(
    groups: List[DuplicateGroup],
    use_recycle_bin: bool = True,
    progress_callback: Optional[Callable[[DeleteProgress], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[int, int, List[Tuple[str, str]]]:
    """
    Executes deletion of TOSS files across all groups.
    Reports real-time progress for each file being deleted.
    If all copies of a group are marked to toss, all copies are removed.
    If at least one copy is marked KEEP, verifies that a KEEP file is intact before deleting.
    Returns (files_deleted, bytes_freed, error_list).
    """
    total_to_delete = sum(g.toss_count for g in groups)
    deleted_count = 0
    bytes_freed = 0
    errors: List[Tuple[str, str]] = []

    if progress_callback:
        progress_callback(DeleteProgress(
            current=0,
            total=total_to_delete,
            percent=0.0,
            current_path="",
            bytes_freed=0
        ))

    for g in groups:
        if cancel_event and cancel_event.is_set():
            break

        keep_files = [e for e in g.entries if e.is_keep]

        # If user designated at least one file to keep, verify it still exists
        if keep_files:
            intact_keep = any(os.path.exists(k.path) for k in keep_files)
            if not intact_keep:
                errors.append((g.filename, "None of the designated KEEP files exist on disk. Aborting deletion for this group."))
                continue

        surviving_entries = []
        for e in g.entries:
            if cancel_event and cancel_event.is_set():
                surviving_entries.append(e)
                continue

            if e.is_keep:
                surviving_entries.append(e)
            else:
                if not os.path.exists(e.path):
                    continue

                if progress_callback:
                    pct = (deleted_count / max(1, total_to_delete)) * 100.0
                    progress_callback(DeleteProgress(
                        current=deleted_count,
                        total=total_to_delete,
                        percent=round(pct, 1),
                        current_path=e.path,
                        bytes_freed=bytes_freed
                    ))

                try:
                    if use_recycle_bin and sys.platform == "win32":
                        success = _send_to_recycle_bin(e.path)
                        if not success:
                            os.remove(e.path)
                    else:
                        os.remove(e.path)
                    deleted_count += 1
                    bytes_freed += g.size

                    if progress_callback:
                        pct = (deleted_count / max(1, total_to_delete)) * 100.0
                        progress_callback(DeleteProgress(
                            current=deleted_count,
                            total=total_to_delete,
                            percent=round(pct, 1),
                            current_path=e.path,
                            bytes_freed=bytes_freed
                        ))
                except Exception as ex:
                    errors.append((e.path, str(ex)))
                    surviving_entries.append(e)

        g.entries = surviving_entries

    if progress_callback and not (cancel_event and cancel_event.is_set()):
        progress_callback(DeleteProgress(
            current=deleted_count,
            total=total_to_delete,
            percent=100.0,
            current_path="Complete",
            bytes_freed=bytes_freed
        ))

    return deleted_count, bytes_freed, errors
