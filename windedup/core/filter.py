import os
import fnmatch
from typing import List, Optional
from windedup.core.models import FileEntry, DuplicateGroup

def parse_masks(mask_str: str) -> List[str]:
    """Splits semicolon-separated masks, stripping whitespace and discarding empty items."""
    if not mask_str:
        return []
    return [m.strip() for m in mask_str.split(";") if m.strip()]

def match_single_mask(path: str, mask: str) -> bool:
    """
    Checks if a file path matches a given glob mask.
    Case-insensitive, normalizes Windows and Unix path separators.
    - If mask contains path separators (e.g. 'docs\\*' or 'node_modules/'), matches against full path.
    - If mask has no path separators (e.g. '*.png' or '*temp*'), matches filename and path components.
    """
    if not mask or not path:
        return False

    norm_path = os.path.normpath(path).lower()
    basename = os.path.basename(norm_path)
    norm_mask = mask.replace("/", "\\").strip().lower()

    has_sep = "\\" in norm_mask

    if has_sep:
        # Path-level pattern
        pattern = norm_mask
        if not pattern.startswith("*") and not (len(pattern) >= 2 and pattern[1] == ":"):
            pattern = "*" + pattern
        if not pattern.endswith("*"):
            pattern = pattern + "*"
        return fnmatch.fnmatch(norm_path, pattern)
    else:
        # Name- or token-level pattern
        if "*" in norm_mask or "?" in norm_mask:
            return fnmatch.fnmatch(basename, norm_mask) or fnmatch.fnmatch(norm_path, f"*{norm_mask}*")
        else:
            # Substring match on path or exact filename match
            return (norm_mask == basename) or (norm_mask in norm_path)

def filter_file_entry(entry: FileEntry, include_masks: List[str], exclude_masks: List[str]) -> bool:
    """Evaluates whether a FileEntry passes the active include and exclude mask lists."""
    # 1. Exclude masks: any match rejects the file
    for exc in exclude_masks:
        if match_single_mask(entry.path, exc):
            return False

    # 2. Include masks: if specified, must match at least one
    if include_masks:
        matched_include = False
        for inc in include_masks:
            if match_single_mask(entry.path, inc):
                matched_include = True
                break
        if not matched_include:
            return False

    return True

def filter_duplicate_groups(
    groups: List[DuplicateGroup],
    include_masks: List[str],
    exclude_masks: List[str]
) -> List[DuplicateGroup]:
    """
    Filters all duplicate groups by include and exclude masks.
    Only groups that retain 2 or more files after filtering are returned as duplicate groups.
    Preserves original entry Keep/Toss designations.
    """
    if not include_masks and not exclude_masks:
        return groups

    filtered_groups: List[DuplicateGroup] = []
    for g in groups:
        surviving_entries = [
            e for e in g.entries
            if filter_file_entry(e, include_masks, exclude_masks)
        ]
        if len(surviving_entries) >= 2:
            new_group = DuplicateGroup(
                group_id=g.group_id,
                hash=g.hash,
                size=g.size,
                entries=surviving_entries
            )
            filtered_groups.append(new_group)

    return filtered_groups
