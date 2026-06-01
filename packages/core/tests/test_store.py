"""Tests for AtomicStore, FileLock, and Checkpoint."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from hermes_core import AtomicStore, Checkpoint, FileLock
from hermes_core.exceptions import StoreError


# ─────────────────────────── AtomicStore ───────────────────────────────────


class TestAtomicStoreBasic:
    def test_set_and_get(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            store.set("hello", "world")
            assert store.get("hello") == "world"

    def test_get_missing_returns_none(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            assert store.get("no_such_key") is None

    def test_set_many(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            store.set_many({"a": "1", "b": "2", "c": "3"})
            assert store.get_all() == {"a": "1", "b": "2", "c": "3"}

    def test_overwrite(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            store.set("k", "v1")
            store.set("k", "v2")
            assert store.get("k") == "v2"

    def test_delete_existing(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            store.set("x", "42")
            deleted = store.delete("x")
            assert deleted is True
            assert store.get("x") is None

    def test_delete_missing(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            assert store.delete("ghost") is False

    def test_keys(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            store.set_many({"b": "B", "a": "A"})
            assert store.keys() == ["a", "b"]

    def test_contains(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            store.set("present", "yes")
            assert "present" in store
            assert "absent" not in store

    def test_getitem_setitem(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            store["mykey"] = "myval"
            assert store["mykey"] == "myval"

    def test_getitem_missing_raises_keyerror(self, tmp_path: Path) -> None:
        with AtomicStore(tmp_path / "state.db") as store:
            with pytest.raises(KeyError):
                _ = store["no_such_key"]

    def test_not_open_raises_store_error(self, tmp_path: Path) -> None:
        store = AtomicStore(tmp_path / "state.db")
        with pytest.raises(StoreError):
            store.set("k", "v")

    def test_backup_file_created(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        with AtomicStore(db_path) as store:
            store.set("init", "true")
            store.set("second", "write")  # triggers backup
        bak = db_path.with_suffix(".bak")
        assert bak.exists()

    def test_persistence_across_open_close(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        with AtomicStore(db_path) as store:
            store.set("persistent", "yes")
        with AtomicStore(db_path) as store:
            assert store.get("persistent") == "yes"


class TestAtomicStoreConcurrency:
    def test_concurrent_writes_are_serialised(self, tmp_path: Path) -> None:
        """Multiple threads writing should not corrupt the database."""
        db_path = tmp_path / "concurrent.db"
        errors: list[Exception] = []
        writes = 20

        def writer(n: int) -> None:
            try:
                with AtomicStore(db_path, lock_timeout=15.0) as s:
                    s.set(f"key_{n}", str(n))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(writes)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during concurrent writes: {errors}"

        with AtomicStore(db_path) as store:
            all_keys = store.keys()
        assert len(all_keys) == writes


# ─────────────────────────── FileLock ──────────────────────────────────────


class TestFileLock:
    def test_basic_acquire_release(self, tmp_path: Path) -> None:
        lock_path = tmp_path / "test.lock"
        with FileLock(lock_path):
            assert lock_path.exists()

    def test_reentrant_from_separate_instance_blocks(self, tmp_path: Path) -> None:
        """Second FileLock instance on the same file should time out."""
        from hermes_core.exceptions import LockError

        lock_path = tmp_path / "blocking.lock"
        acquired_inner = threading.Event()
        release_inner = threading.Event()

        def hold_lock() -> None:
            with FileLock(lock_path, timeout=5.0):
                acquired_inner.set()
                release_inner.wait(timeout=5.0)

        t = threading.Thread(target=hold_lock)
        t.start()
        acquired_inner.wait(timeout=3.0)

        with pytest.raises(LockError):
            # Timeout quickly — the lock is held by the other thread.
            FileLock(lock_path, timeout=0.1).acquire()

        release_inner.set()
        t.join()

    def test_stale_lock_cleared(self, tmp_path: Path) -> None:
        """A lock file referencing a dead PID should be cleared and re-acquired."""
        lock_path = tmp_path / "stale.lock"
        # Write a PID that will never exist (PID 1 is init, but we use an
        # impossibly high PID to guarantee it's not running).
        lock_path.write_text("99999999")

        fl = FileLock(lock_path, timeout=2.0)
        # Should NOT raise — stale lock is detected and cleared.
        fl.acquire()
        fl.release()


# ─────────────────────────── Checkpoint ────────────────────────────────────


class TestCheckpoint:
    def test_save_and_list(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        with AtomicStore(db_path) as store:
            store.set("foo", "bar")
            ckpt = Checkpoint(store, checkpoints_dir=tmp_path / "ckpts")
            info = ckpt.save("snap1")
            assert info.name == "snap1"
            infos = ckpt.list()
            assert any(i.name == "snap1" for i in infos)

    def test_restore_rolls_back(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        ckpt_dir = tmp_path / "ckpts"

        with AtomicStore(db_path) as store:
            store.set("version", "1")
            ckpt = Checkpoint(store, checkpoints_dir=ckpt_dir)
            ckpt.save("v1")
            store.set("version", "2")
            assert store.get("version") == "2"
            ckpt.restore("v1")
            assert store.get("version") == "1"

    def test_restore_nonexistent_raises(self, tmp_path: Path) -> None:
        from hermes_core.exceptions import CheckpointError

        db_path = tmp_path / "state.db"
        with AtomicStore(db_path) as store:
            store.set("k", "v")
            ckpt = Checkpoint(store)
            with pytest.raises(CheckpointError):
                ckpt.restore("does_not_exist")

    def test_prune(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        ckpt_dir = tmp_path / "ckpts"
        with AtomicStore(db_path) as store:
            store.set("x", "0")
            ckpt = Checkpoint(store, checkpoints_dir=ckpt_dir)
            for i in range(6):
                store.set("x", str(i))
                ckpt.save(f"snap{i}")
            deleted = ckpt.prune(keep=3)
            assert deleted == 3
            assert len(ckpt.list()) == 3

    def test_invalid_name_raises(self, tmp_path: Path) -> None:
        db_path = tmp_path / "state.db"
        with AtomicStore(db_path) as store:
            store.set("k", "v")
            ckpt = Checkpoint(store)
            with pytest.raises(ValueError):
                ckpt.save("bad/name")
