"""AtomicStore — crash-safe SQLite state store with WAL mode.

Write pattern
-------------
1. Acquire :class:`~hermes_core.lock.FileLock` on ``<db>.lock``.
2. Write new state to a temp file (``<db>.tmp``).
3. ``fsync`` the temp file.
4. ``rename`` temp → ``<db>.bak`` (backup of previous state).
5. ``rename`` ``<db>.bak`` → main db path.
6. Re-open connection with WAL pragma applied.

This guarantees that at any crash point, either the old state or the new
state is available intact — never a half-written file.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import structlog

from hermes_core.exceptions import StoreError
from hermes_core.lock import FileLock

log = structlog.get_logger(__name__)

_WAL_PRAGMAS = (
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA temp_store=MEMORY;",
    "PRAGMA mmap_size=134217728;",  # 128 MiB
    "PRAGMA cache_size=-8000;",     # ~8 MiB page cache
    "PRAGMA foreign_keys=ON;",
)

_STATE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS state (
    key   TEXT NOT NULL,
    value TEXT NOT NULL,
    ts    INTEGER NOT NULL DEFAULT (unixepoch()),
    PRIMARY KEY (key)
);
"""

_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_state_ts ON state (ts);
"""


class AtomicStore:
    """Durable key-value store backed by SQLite in WAL mode.

    Every mutation is performed via a temp-file → fsync → rename sequence
    so that the database file is *never* left in a partially-written state.
    Concurrent writers are serialised with :class:`~hermes_core.lock.FileLock`.

    Parameters
    ----------
    path:
        Filesystem path to the SQLite database file.  The parent directory
        is created on first use.
    lock_timeout:
        Seconds to wait for the exclusive write lock.

    Examples
    --------
    >>> store = AtomicStore("/tmp/hermes/state.db")
    >>> with store:
    ...     store.set("key", "value")
    ...     assert store.get("key") == "value"
    """

    def __init__(
        self,
        path: str | Path,
        lock_timeout: float = 30.0,
    ) -> None:
        self.path = Path(path)
        self._lock_path = self.path.with_suffix(".lock")
        self._bak_path = self.path.with_suffix(".bak")
        self._lock = FileLock(self._lock_path, timeout=lock_timeout)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------ #
    # Context-manager protocol                                             #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def open(self) -> None:
        """Open (or create) the database and apply WAL pragmas."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = self._open_connection(self.path)
        self._bootstrap_schema()
        log.info("atomic_store.opened", path=str(self.path))

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            with contextlib.suppress(sqlite3.Error):
                self._conn.close()
            self._conn = None
            log.debug("atomic_store.closed", path=str(self.path))

    # ------------------------------------------------------------------ #
    # Read API                                                             #
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> str | None:
        """Return the value for *key*, or ``None`` if not found.

        Parameters
        ----------
        key:
            The state key to look up.
        """
        self._ensure_open()
        assert self._conn is not None  # mypy narrowing
        cur = self._conn.execute("SELECT value FROM state WHERE key = ?", (key,))
        row = cur.fetchone()
        return str(row[0]) if row else None

    def get_all(self) -> dict[str, str]:
        """Return every key-value pair currently stored."""
        self._ensure_open()
        assert self._conn is not None
        cur = self._conn.execute("SELECT key, value FROM state ORDER BY key")
        return {row[0]: row[1] for row in cur.fetchall()}

    def keys(self) -> list[str]:
        """Return all stored keys in alphabetical order."""
        self._ensure_open()
        assert self._conn is not None
        cur = self._conn.execute("SELECT key FROM state ORDER BY key")
        return [row[0] for row in cur.fetchall()]

    # ------------------------------------------------------------------ #
    # Write API                                                            #
    # ------------------------------------------------------------------ #

    def set(self, key: str, value: str) -> None:
        """Atomically set *key* to *value*.

        Uses the write-temp → backup → rename pattern under a file lock.

        Parameters
        ----------
        key:
            The state key.
        value:
            The string value to store.

        Raises
        ------
        StoreError
            If the atomic write sequence fails at any step.
        """
        self.set_many({key: value})

    def set_many(self, items: dict[str, str]) -> None:
        """Atomically store multiple key-value pairs in a single transaction.

        Parameters
        ----------
        items:
            Mapping of key → value pairs to upsert.

        Raises
        ------
        StoreError
            If the atomic write sequence fails at any step.
        """
        if not items:
            return

        self._ensure_open()
        log.debug("atomic_store.set_many", keys=list(items.keys()), count=len(items))

        with self._lock:
            self._atomic_write(items)

        self._reindex()

    def delete(self, key: str) -> bool:
        """Delete *key* from the store.

        Parameters
        ----------
        key:
            The key to remove.

        Returns
        -------
        bool
            ``True`` if the key existed and was deleted, ``False`` otherwise.
        """
        self._ensure_open()
        assert self._conn is not None

        with self._lock:
            with self._conn:
                cur = self._conn.execute("DELETE FROM state WHERE key = ?", (key,))
                deleted = cur.rowcount > 0

        if deleted:
            log.debug("atomic_store.deleted", key=key)
            self._reindex()
        return deleted

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _ensure_open(self) -> None:
        if self._conn is None:
            raise StoreError("Store is not open. Call open() or use as a context manager.")

    def _open_connection(self, path: Path) -> sqlite3.Connection:
        """Open a connection and apply WAL-mode pragmas."""
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        for pragma in _WAL_PRAGMAS:
            conn.execute(pragma)
        conn.commit()
        return conn

    def _bootstrap_schema(self) -> None:
        """Create the state table and index if they do not exist."""
        assert self._conn is not None
        with self._conn:
            self._conn.execute(_STATE_TABLE_DDL)
            self._conn.execute(_INDEX_DDL)

    def _atomic_write(self, items: dict[str, str]) -> None:
        """Write *items* via temp-file → backup → rename.

        Steps
        -----
        1. Copy existing DB to a temp file.
        2. Apply upserts to the temp file.
        3. ``fsync`` the temp file.
        4. Rename existing DB to ``.bak``.
        5. Rename temp file to DB path.
        6. Re-attach ``self._conn`` to the new file.
        """
        assert self._conn is not None
        parent = self.path.parent

        try:
            # ── Step 1: copy current DB to temp ─────────────────────────
            tmp_fd, tmp_path_str = tempfile.mkstemp(
                dir=parent, prefix=".hermes_tmp_", suffix=".db"
            )
            tmp_path = Path(tmp_path_str)
            try:
                os.close(tmp_fd)
                if self.path.exists():
                    shutil.copy2(str(self.path), str(tmp_path))

                # ── Step 2: apply writes to temp ────────────────────────
                tmp_conn = self._open_connection(tmp_path)
                tmp_conn.execute(_STATE_TABLE_DDL)
                tmp_conn.execute(_INDEX_DDL)
                with tmp_conn:
                    for key, value in items.items():
                        tmp_conn.execute(
                            """
                            INSERT INTO state (key, value, ts)
                            VALUES (?, ?, unixepoch())
                            ON CONFLICT(key) DO UPDATE SET
                                value = excluded.value,
                                ts    = excluded.ts
                            """,
                            (key, value),
                        )
                tmp_conn.execute("PRAGMA wal_checkpoint(FULL);")
                tmp_conn.commit()

                # ── Step 3: fsync the temp file ──────────────────────────
                tmp_fd2 = os.open(str(tmp_path), os.O_RDWR)
                try:
                    os.fsync(tmp_fd2)
                finally:
                    os.close(tmp_fd2)

                tmp_conn.close()

                # ── Step 4 + 5: atomic rename ────────────────────────────
                # Backup the existing DB, then move temp into place.
                if self.path.exists():
                    os.replace(str(self.path), str(self._bak_path))
                os.replace(str(tmp_path), str(self.path))

            except Exception:
                # Clean up temp on failure.
                with contextlib.suppress(OSError):
                    tmp_path.unlink(missing_ok=True)
                raise

            # ── Step 6: re-attach connection ────────────────────────────
            self._conn.close()
            self._conn = self._open_connection(self.path)

        except sqlite3.Error as exc:
            raise StoreError(f"Atomic write failed: {exc}") from exc

    def _reindex(self) -> None:
        """Rebuild the index; called after every successful mutation."""
        assert self._conn is not None
        try:
            with self._conn:
                self._conn.execute("REINDEX idx_state_ts;")
        except sqlite3.Error as exc:
            log.warning("atomic_store.reindex_failed", error=str(exc))

    # ------------------------------------------------------------------ #
    # Dunder helpers                                                       #
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        status = "open" if self._conn is not None else "closed"
        return f"AtomicStore(path={self.path!r}, status={status!r})"

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self.get(key) is not None

    def __getitem__(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: str) -> None:
        self.set(key, value)

    def execute_raw(self, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
        """Execute arbitrary SQL and return all rows (read-only use recommended).

        Parameters
        ----------
        sql:
            SQL statement to execute.
        params:
            Positional bind parameters.
        """
        self._ensure_open()
        assert self._conn is not None
        cur = self._conn.execute(sql, params)
        return cur.fetchall()
