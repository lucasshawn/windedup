from typing import List
import os
from windedup.core.models import DuplicateGroup

def apply_keep_newest(groups: List[DuplicateGroup]) -> None:
    """Keeps the file with highest mtime in each group; marks others as toss."""
    for g in groups:
        if not g.entries:
            continue
        newest = max(g.entries, key=lambda e: e.mtime)
        for e in g.entries:
            e.is_keep = (e == newest)

def apply_keep_oldest(groups: List[DuplicateGroup]) -> None:
    """Keeps the file with lowest mtime in each group; marks others as toss."""
    for g in groups:
        if not g.entries:
            continue
        oldest = min(g.entries, key=lambda e: e.mtime)
        for e in g.entries:
            e.is_keep = (e == oldest)

def apply_keep_shortest_path(groups: List[DuplicateGroup]) -> None:
    """Keeps the file with shortest path length / least path depth."""
    for g in groups:
        if not g.entries:
            continue
        shortest = min(g.entries, key=lambda e: (len(e.path.split(os.sep)), len(e.path)))
        for e in g.entries:
            e.is_keep = (e == shortest)

def apply_prefer_folder(groups: List[DuplicateGroup], folder_prefix: str) -> None:
    """Keeps files residing inside folder_prefix. If none or all match, falls back to first."""
    normalized_prefix = os.path.normcase(os.path.abspath(folder_prefix))
    for g in groups:
        if not g.entries:
            continue
        matches = [e for e in g.entries if os.path.normcase(os.path.abspath(e.path)).startswith(normalized_prefix)]
        chosen = matches[0] if matches else g.entries[0]
        for e in g.entries:
            e.is_keep = (e == chosen)
