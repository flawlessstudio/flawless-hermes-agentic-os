"""FileLock — POSIX file-locking via fcntl.flock with timeout and stale-PID detection.

The lock file stores the owning PID so that stale locks (process died without
unlocking) are detected automatically.
"""

from __future__ import annotations

import errno
import fcntl
import os
import time
from pathlib import Path
from types import TracebackType
from typing import Self

import structlog

from hermes_core.exceptions import LockError

log = structlog.get_logger(__name__)

_DEFAULT_TIMEOUT: float = 30.0
_DEFAULT_RETRY_INTERVAL: float = 0.05  # 50 ms


class FileLock:
    """Exclusive file lock using ``fcntl.LOCK_EX`` (non-blocking + retry loop).

    Usage::

        with FileLock("/tmp/hermes.lock", timeout=10):
            ...  # exclusive section

    Stale lock detection
    --------------------
    The lock file contains the PID of the owning process.  If the lock file
    exists but the PID is not running, it is considered stale and overwritten.

    Parameters
    ----------
    path:
        Path to the lock file (created on demand).
    timeout:
        Seconds to wait before raising :class:`LockError`.
    retry_interval:
        Seconds to sleep between lock attempts.
    """

    def __init__(
        self,
        path: str | Path,
        timeout: float = _DEFAULT_TIMEOUT,
        retry_interval: float = _DEFAULT_RETRY_INTERVAL,
    ) -> None:
        self.path = Path(path)
        self.timeout = timeout
        self.retry_interval = retry_interval
        self._fd: int | None = None

    # ------------------------------------------------------------------ #
    # Context-manager protocol                                             #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def acquire(self) -> None:
        """Acquire the exclusive lock, waiting up to *timeout* seconds.

        Raises
        ------
        LockError
            If the lock cannot be acquired within *timeout* seconds.
        """
        self._clear_if_stale()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        deadline = time.monotonic() + self.timeout
        self._fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o600)

        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Write our PID into the lock file so stale detection works.
                os.ftruncate(self._fd, 0)
                os.write(self._fd, str(os.getpid()).encode())
                os.fsync(self._fd)
                log.debug("file_lock.acquired", path=str(self.path), pid=os.getpid())
                return
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.monotonic() >= deadline:
                    os.close(self._fd)
                    self._fd = None
                    raise LockError(
                        f"Could not acquire lock on {self.path!r} within {self.timeout}s"
                    ) from exc
                time.sleep(self.retry_interval)

    def release(self) -> None:
        """Release the lock and close the file descriptor."""
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            log.debug("file_lock.released", path=str(self.path))
        except OSError:
            log.warning("file_lock.release_failed", path=str(self.path), exc_info=True)
        finally:
            self._fd = None

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _clear_if_stale(self) -> None:
        """Remove the lock file if it belongs to a dead process."""
        if not self.path.exists():
            return
        try:
            raw = self.path.read_text().strip()
            if not raw:
                return
            pid = int(raw)
            # Signal 0 checks existence without sending a signal.
            os.kill(pid, 0)
        except (ValueError, PermissionError):
            # PID is running (permission denied → process exists)
            return
        except ProcessLookupError:
            log.warning("file_lock.stale_detected", path=str(self.path), stale_pid=raw)
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass
