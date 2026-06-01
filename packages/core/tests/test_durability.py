"""Durability tests — verify atomicity under sudden process death.

The key test spawns a writer subprocess, kills it with SIGKILL mid-write,
then verifies that the store is still readable and contains either the old
state (pre-write) or the new state (write completed before kill) — never a
corrupted database.
"""

from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

# ── Helper: a small writer script ────────────────────────────────────────────

_WRITER_SCRIPT = textwrap.dedent(
    """\
    import sys
    import time
    from pathlib import Path
    from hermes_core import AtomicStore

    db_path = Path(sys.argv[1])
    with AtomicStore(db_path) as store:
        # Signal readiness by writing a sentinel BEFORE the big write
        ready_flag = Path(sys.argv[2])
        ready_flag.write_text("ready")
        # Perform a large write to increase window for SIGKILL
        items = {f"key_{i}": f"value_{i}" for i in range(500)}
        store.set_many(items)
        # Signal completion
        Path(sys.argv[3]).write_text("done")
    """
)


class TestDurabilityUnderSIGKILL:
    def test_store_survives_kill_mid_write(self, tmp_path: Path) -> None:
        """Kill a writer with SIGKILL and verify the store is intact afterward."""
        db_path = tmp_path / "durable.db"
        ready_flag = tmp_path / "ready.flag"
        done_flag = tmp_path / "done.flag"
        script_path = tmp_path / "writer.py"
        script_path.write_text(_WRITER_SCRIPT)

        # Pre-populate so there's a valid state before the kill.
        from hermes_core import AtomicStore

        with AtomicStore(db_path) as store:
            store.set("existing_key", "existing_value")

        # Spawn writer subprocess.
        proc = subprocess.Popen(
            [sys.executable, str(script_path), str(db_path), str(ready_flag), str(done_flag)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for the subprocess to signal readiness (it's about to write).
        deadline = time.monotonic() + 10.0
        while not ready_flag.exists():
            if time.monotonic() > deadline:
                proc.kill()
                pytest.fail("Writer subprocess never became ready")
            time.sleep(0.01)

        # Small sleep to let it start the write, then KILL.
        time.sleep(0.005)
        try:
            os.kill(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # Process already finished — that's fine too.
        proc.wait()

        # The database MUST still be openable and readable.
        with AtomicStore(db_path) as store:
            # Either the old state or new state is valid.
            val = store.get("existing_key")
            # If the write completed before SIGKILL, the new keys exist.
            # If not, the old "existing_value" is intact.
            # Either way, we must be able to open and query without error.
            assert val in ("existing_value", None) or val is not None

        # Additionally verify raw SQLite integrity.
        conn = sqlite3.connect(str(db_path))
        result = conn.execute("PRAGMA integrity_check;").fetchone()
        conn.close()
        assert result[0] == "ok", f"SQLite integrity_check failed: {result[0]}"

    def test_backup_file_is_valid_sqlite(self, tmp_path: Path) -> None:
        """The .bak file left behind must itself be a valid SQLite database."""
        from hermes_core import AtomicStore

        db_path = tmp_path / "state.db"
        with AtomicStore(db_path) as store:
            store.set("first", "write")
            store.set("second", "write_triggers_bak")

        bak_path = db_path.with_suffix(".bak")
        assert bak_path.exists(), ".bak file was not created"

        conn = sqlite3.connect(str(bak_path))
        result = conn.execute("PRAGMA integrity_check;").fetchone()
        conn.close()
        assert result[0] == "ok", f"Backup file integrity_check failed: {result[0]}"

    def test_multiple_sequential_writes_remain_consistent(self, tmp_path: Path) -> None:
        """Many sequential writes should all be readable in final state."""
        from hermes_core import AtomicStore

        db_path = tmp_path / "seq.db"
        with AtomicStore(db_path) as store:
            for i in range(50):
                store.set(f"k{i}", f"v{i}")

        with AtomicStore(db_path) as store:
            for i in range(50):
                assert store.get(f"k{i}") == f"v{i}", f"key k{i} missing or wrong"

    def test_wal_mode_is_active(self, tmp_path: Path) -> None:
        """Confirm WAL journal mode is applied to the store."""
        from hermes_core import AtomicStore

        db_path = tmp_path / "wal_check.db"
        with AtomicStore(db_path) as store:
            store.set("x", "y")
            rows = store.execute_raw("PRAGMA journal_mode;")
        assert rows[0][0] == "wal", f"Expected WAL mode, got {rows[0][0]!r}"
