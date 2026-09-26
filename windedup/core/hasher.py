import hashlib
from typing import Optional
import threading

DEFAULT_CHUNK_SIZE = 65536  # 64 KB

def compute_partial_hash(filepath: str, sample_size: int = DEFAULT_CHUNK_SIZE) -> Optional[str]:
    """Reads up to sample_size bytes and returns the SHA-256 hex digest. Returns None on error."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(sample_size)
            return hashlib.sha256(chunk).hexdigest()
    except (OSError, PermissionError):
        return None

def compute_full_hash(
    filepath: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    cancel_event: Optional[threading.Event] = None
) -> Optional[str]:
    """Streams the full file in chunks and returns SHA-256 hex digest. Returns None on error or cancel."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while True:
                if cancel_event and cancel_event.is_set():
                    return None
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None
