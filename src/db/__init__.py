"""Database package exports and compatibility helpers.

Provide lightweight exception classes that tests expect to import, and
re-export common symbols from submodules for convenience.
"""
from typing import TYPE_CHECKING

# Lightweight exceptions used by tests and callers
class DatabaseConnectionError(Exception):
    """Raised when a database connection cannot be established."""
    pass


class DatabaseSchemaError(Exception):
    """Raised when initializing or validating DB schema fails."""
    pass

# Re-export DatabaseManager and SCHEMAS if available
try:
    from .manager import DatabaseManager  # type: ignore
except Exception:  # pragma: no cover - best-effort import
    DatabaseManager = None  # type: ignore

try:
    from .schema import SCHEMAS  # type: ignore
except Exception:  # pragma: no cover - best-effort import
    SCHEMAS = {}

__all__ = [
    "DatabaseConnectionError",
    "DatabaseSchemaError",
    "DatabaseManager",
    "SCHEMAS",
]
