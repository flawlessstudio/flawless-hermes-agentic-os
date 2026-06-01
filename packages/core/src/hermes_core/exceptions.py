"""Exception hierarchy for hermes_core."""

from __future__ import annotations


class HermesError(Exception):
    """Base class for all Hermes exceptions."""


class StoreError(HermesError):
    """Raised when an atomic store operation fails."""


class LockError(HermesError):
    """Raised when a file lock cannot be acquired within the timeout."""


class CheckpointError(HermesError):
    """Raised when a checkpoint or rollback operation fails."""
