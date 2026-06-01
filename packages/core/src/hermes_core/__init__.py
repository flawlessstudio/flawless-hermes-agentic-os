"""hermes_core — atomic SQLite state store, file locking, and checkpoint/rollback.

Public API
----------
- AtomicStore  : durable, crash-safe SQLite wrapper
- FileLock     : POSIX file-lock context manager with timeout + stale-detection
- Checkpoint   : snapshot/rollback manager
- HermesError, StoreError, LockError, CheckpointError : exception hierarchy
"""

from hermes_core.checkpoint import Checkpoint
from hermes_core.exceptions import CheckpointError, HermesError, LockError, StoreError
from hermes_core.lock import FileLock
from hermes_core.store import AtomicStore

__all__ = [
    "AtomicStore",
    "Checkpoint",
    "CheckpointError",
    "FileLock",
    "HermesError",
    "LockError",
    "StoreError",
]
