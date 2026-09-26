import os
import threading
import logging
from collections import defaultdict
from typing import List, Callable, Optional, Dict
from windedup.core.models import FileEntry, DuplicateGroup, ScanProgress
from windedup.core.hasher import compute_partial_hash, compute_full_hash

def scan_directory(
    root_dir: str,
    progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> List[DuplicateGroup]:
    """
    Recursively scans root_dir for duplicate files using 3-stage hashing:
    1. Size matching
    2. 64KB partial hash
    3. Full SHA-256 hash
    Emits continuous numerical percent progress updates.
    """
    if not os.path.isdir(root_dir):
        logging.warning(f"scan_directory called with non-existent or invalid directory: '{root_dir}'")
        return []

    logging.info(f"Starting duplicate scan for: {root_dir}")

    # Phase 1: Fast directory traversal & group by size
    size_to_files: Dict[int, List[FileEntry]] = defaultdict(list)
    files_scanned = 0

    if progress_callback:
        progress_callback(ScanProgress(phase="enumerating", percent=0.0, files_scanned=0, current_path=root_dir))

    for dirpath, _, filenames in os.walk(root_dir):
        if cancel_event and cancel_event.is_set():
            logging.info("Scan cancelled during directory traversal.")
            return []
        for name in filenames:
            if cancel_event and cancel_event.is_set():
                logging.info("Scan cancelled during directory traversal.")
                return []
            full_path = os.path.join(dirpath, name)
            try:
                stat = os.stat(full_path)
                size = stat.st_size
                mtime = stat.st_mtime
                entry = FileEntry(path=full_path, size=size, mtime=mtime)
                size_to_files[size].append(entry)
                files_scanned += 1
                if files_scanned % 100 == 0 and progress_callback:
                    progress_callback(ScanProgress(
                        phase="enumerating",
                        percent=0.0,
                        files_scanned=files_scanned,
                        current_path=dirpath
                    ))
            except (OSError, PermissionError) as e:
                logging.debug(f"Cannot access file '{full_path}': {e}")
                continue

    # Filter out files with unique sizes
    candidate_size_groups = [entries for entries in size_to_files.values() if len(entries) >= 2]
    total_candidates = sum(len(entries) for entries in candidate_size_groups)
    logging.info(f"Phase 1 complete: {files_scanned} files inspected, {len(candidate_size_groups)} candidate size groups ({total_candidates} files).")

    if total_candidates == 0:
        if progress_callback:
            progress_callback(ScanProgress(phase="complete", percent=100.0, files_scanned=files_scanned, candidate_count=0))
        return []

    # Phase 2: Partial hash comparison (first 64 KB)
    # Allocation: 0% - 30% progress
    partial_to_files: Dict[tuple, List[FileEntry]] = defaultdict(list)
    processed_candidates = 0

    for entries in candidate_size_groups:
        if cancel_event and cancel_event.is_set():
            return []
        size = entries[0].size
        for entry in entries:
            if cancel_event and cancel_event.is_set():
                return []
            p_hash = compute_partial_hash(entry.path)
            processed_candidates += 1
            if p_hash is not None:
                partial_to_files[(size, p_hash)].append(entry)

            if progress_callback:
                pct = (processed_candidates / total_candidates) * 30.0
                progress_callback(ScanProgress(
                    phase="comparing",
                    percent=round(pct, 1),
                    files_scanned=files_scanned,
                    current_path=entry.path,
                    candidate_count=processed_candidates
                ))

    # Phase 3: Full hash for partial hash collisions
    # Allocation: 30% - 100% progress
    candidate_partial_groups = [entries for entries in partial_to_files.values() if len(entries) >= 2]
    full_candidates_total = sum(len(entries) for entries in candidate_partial_groups)
    logging.info(f"Phase 2 complete: {len(candidate_partial_groups)} partial collision groups ({full_candidates_total} files).")

    full_to_files: Dict[tuple, List[FileEntry]] = defaultdict(list)
    full_processed = 0

    for entries in candidate_partial_groups:
        if cancel_event and cancel_event.is_set():
            logging.info("Scan cancelled during full hashing.")
            return []
        size = entries[0].size
        for entry in entries:
            if cancel_event and cancel_event.is_set():
                logging.info("Scan cancelled during full hashing.")
                return []
            f_hash = compute_full_hash(entry.path, cancel_event=cancel_event)
            full_processed += 1
            if f_hash is not None:
                entry.hash = f_hash
                full_to_files[(size, f_hash)].append(entry)

            if progress_callback:
                pct = 30.0 + ((full_processed / max(1, full_candidates_total)) * 70.0)
                progress_callback(ScanProgress(
                    phase="hashing",
                    percent=min(100.0, round(pct, 1)),
                    files_scanned=files_scanned,
                    current_path=entry.path,
                    candidate_count=full_processed
                ))

    duplicate_groups: List[DuplicateGroup] = []
    group_idx = 1
    for (size, f_hash), entries in full_to_files.items():
        if len(entries) >= 2:
            # Default designation: first is KEEP, remaining are TOSS
            for i, entry in enumerate(entries):
                entry.is_keep = (i == 0)
            group = DuplicateGroup(
                group_id=f"group_{group_idx}",
                hash=f_hash,
                size=size,
                entries=entries
            )
            duplicate_groups.append(group)
            group_idx += 1

    logging.info(f"Scan complete: found {len(duplicate_groups)} duplicate groups across {files_scanned} files.")
    if progress_callback:
        progress_callback(ScanProgress(phase="complete", percent=100.0, files_scanned=files_scanned, candidate_count=len(duplicate_groups)))

    return duplicate_groups
