"""Checkpoint — snapshot and rollback for :class:`~hermes_core.store.AtomicStore`.

A *checkpoint* is a full point-in-time copy of the database.  Checkpoints are
stored under ``<db_dir>/checkpoints/<name>.db`` and can be listed, restored, or
pruned at any time.

Usage::

    ckpt = Checkpoint(store)
    ckpt.save("before_migration")
    try:
        store.set("schema_version", "2")
    except Exception:
        ckpt.restore("before_migration")
        raise
"""

from __future__ import annotations

import shutil
import sqlite3
import time
from pathlib import Path
from typing import NamedTuple

import structlog

from hermes_core.exceptions import CheckpointError
from hermes_core.store import AtomicStore

log = structlog.get_logger(__name__)


class CheckpointInfo(NamedTuple):
    """Metadata returned by :meth:`Checkpoint.list`."""

    name: str
    path: Path
    created_at: float  # Unix timestamp
    size_bytes: int


class Checkpoint:
    """Snapshot/rollback manager for an :class:`~hermes_core.store.AtomicStore`.

    Checkpoints are plain SQLite file copies stored alongside the main database.
    They are cheap (O(db size)) and survive process restarts.

    Parameters
    ----------
    store:
        The :class:`AtomicStore` instance to checkpoint.
    checkpoints_dir:
        Directory for checkpoint files.  Defaults to ``<db_parent>/checkpoints``.
    """

    def __init__(
        self,
        store: AtomicStore,
        checkpoints_dir: str | Path | None = None,
    ) -> None:
        self._store = store
        if checkpoints_dir is None:
            self._dir = store.path.parent / "checkpoints"
        else:
            self._dir = Path(checkpoints_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def save(self, name: str) -> CheckpointInfo:
        """Create a checkpoint named *name*.

        Parameters
        ----------
        name:
            Alphanumeric identifier (no path separators).

        Returns
        -------
        CheckpointInfo
            Metadata of the created checkpoint.

        Raises
        ------
        CheckpointError
            If the checkpoint file cannot be written.
        ValueError
            If *name* contains path-separator characters.
        """
        self._validate_name(name)
        target = self._checkpoint_path(name)

        if not self._store.path.exists():
            raise CheckpointError(f"Store database does not exist yet: {self._store.path}")

        try:
            # Use SQLite's online backup API so we get a consistent snapshot
            # even if a transaction is in progress.
            src_conn = sqlite3.connect(str(self._store.path))
            dst_conn = sqlite3.connect(str(target))
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
        except sqlite3.Error as exc:
            raise CheckpointError(f"Failed to create checkpoint {name!r}: {exc}") from exc

        info = self._make_info(name, target)
        log.info(
            "checkpoint.saved",
            name=name,
            path=str(target),
            size_bytes=info.size_bytes,
        )
        return info

    def restore(self, name: str) -> None:
        """Restore the store to the state captured in checkpoint *name*.

        The current database is backed up as ``<name>.pre_restore.db`` before
        overwriting, providing a safety net.

        Parameters
        ----------
        name:
            Name of an existing checkpoint.

        Raises
        ------
        CheckpointError
            If the checkpoint does not exist or cannot be applied.
        """
        self._validate_name(name)
        src = self._checkpoint_path(name)
        if not src.exists():
            raise CheckpointError(f"Checkpoint not found: {name!r}")

        # Safety: snapshot current state before clobbering it.
        safety_name = f"{name}.pre_restore.{int(time.time())}"
        if self._store.path.exists():
            try:
                self.save(safety_name)
            except CheckpointError:
                log.warning("checkpoint.pre_restore_backup_failed", target=safety_name)

        try:
            self._store.close()
            shutil.copy2(str(src), str(self._store.path))
            self._store.open()
        except OSError as exc:
            raise CheckpointError(f"Failed to restore checkpoint {name!r}: {exc}") from exc

        log.info("checkpoint.restored", name=name, safety_backup=safety_name)

    def list(self) -> list[CheckpointInfo]:
        """Return all available checkpoints, newest first."""
        infos: list[CheckpointInfo] = []
        for p in self._dir.glob("*.db"):
            name = p.stem
            infos.append(self._make_info(name, p))
        return sorted(infos, key=lambda i: i.created_at, reverse=True)

    def delete(self, name: str) -> bool:
        """Delete checkpoint *name*.

        Returns
        -------
        bool
            ``True`` if the checkpoint existed and was deleted.
        """
        self._validate_name(name)
        target = self._checkpoint_path(name)
        if target.exists():
            target.unlink()
            log.info("checkpoint.deleted", name=name)
            return True
        return False

    def prune(self, keep: int = 5) -> int:
        """Remove oldest checkpoints, retaining at most *keep*.

        Parameters
        ----------
        keep:
            Number of most-recent checkpoints to keep.

        Returns
        -------
        int
            Number of checkpoints deleted.
        """
        all_ckpts = self.list()
        to_delete = all_ckpts[keep:]
        for info in to_delete:
            info.path.unlink(missing_ok=True)
            log.debug("checkpoint.pruned", name=info.name)
        return len(to_delete)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _checkpoint_path(self, name: str) -> Path:
        return self._dir / f"{name}.db"

    @staticmethod
    def _validate_name(name: str) -> None:
        if any(c in name for c in ("/", "\\", "\0")):
            raise ValueError(f"Checkpoint name must not contain path separators: {name!r}")

    @staticmethod
    def _make_info(name: str, path: Path) -> CheckpointInfo:
        stat = path.stat()
        return CheckpointInfo(
            name=name,
            path=path,
            created_at=stat.st_mtime,
            size_bytes=stat.st_size,
        )
