from dataclasses import dataclass, field
from typing import List, Optional
import os

@dataclass
class FileEntry:
    path: str
    size: int
    mtime: float
    hash: Optional[str] = None
    is_keep: bool = True

@dataclass
class DuplicateGroup:
    group_id: str
    hash: str
    size: int
    entries: List[FileEntry] = field(default_factory=list)

    @property
    def filename(self) -> str:
        if self.entries:
            return os.path.basename(self.entries[0].path)
        return ""

    @property
    def keep_count(self) -> int:
        return sum(1 for e in self.entries if e.is_keep)

    @property
    def toss_count(self) -> int:
        return sum(1 for e in self.entries if not e.is_keep)

    @property
    def reclaimable_bytes(self) -> int:
        return self.toss_count * self.size

@dataclass
class ScanProgress:
    phase: str  # "enumerating" | "comparing" | "hashing" | "complete"
    percent: float  # 0.0 to 100.0
    files_scanned: int
    current_path: str = ""
    candidate_count: int = 0
