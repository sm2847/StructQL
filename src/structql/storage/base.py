"""
StorageEngine interface (Protocol).

This is the Dependency Inversion boundary of the whole project: the
executor (M6) and importer depend on this abstract interface, never on a
concrete storage implementation. That means:
  - Tests use InMemoryStorageEngine (storage/memory.py) - fast, no cleanup.
  - A future file-backed engine can be dropped in without touching the
    executor, importer, or CLI (Open/Closed Principle).

Design decision: this is a row-oriented interface (create_table /
insert_rows / scan_rows), not a query-aware one. A method like
`select(table, predicate)` was considered and rejected - it would push
WHERE-clause evaluation into the storage layer, which blurs the boundary
we're trying to keep sharp: storage's only job is "remember rows and give
them back", nothing about how a query decides which rows match.

Implemented as a typing.Protocol rather than an abc.ABC: any class with
these methods satisfies StorageEngine structurally, without needing to
explicitly subclass it. This keeps InMemoryStorageEngine and any future
FileStorageEngine fully independent of each other and of this module.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from structql.domain.row import Row
from structql.domain.schema import Schema


@runtime_checkable
class StorageEngine(Protocol):
    def create_table(self, schema: Schema) -> None:
        """Register a new table with the given schema.

        Raises StorageError if a table with this name already exists -
        redefining a table's shape out from under existing data is a bug
        worth catching immediately, not something to silently allow.
        """
        ...

    def insert_rows(self, table_name: str, rows: list[Row]) -> None:
        """Append rows to an existing table.

        Takes a list rather than a single row because the primary caller
        (the CSV importer) always has a full batch ready at once - one
        call per import avoids forcing callers into a per-row loop for the
        common case, while single-row inserts remain trivial (pass a
        one-item list).

        Raises StorageError if the table doesn't exist.
        """
        ...

    def scan_rows(self, table_name: str) -> list[Row]:
        """Return all rows in a table, in insertion order.

        This is the only read path in v1 - there is no indexed lookup, so
        every query does a full scan here and filters in the executor.
        That's the deliberate v1 trade-off noted in the README; the
        interface doesn't preclude adding an indexed lookup method later.

        Raises StorageError if the table doesn't exist.
        """
        ...

    def get_schema(self, table_name: str) -> Schema:
        """Return the schema a table was created with.

        Raises StorageError if the table doesn't exist.
        """
        ...

    def list_tables(self) -> list[str]:
        """Return the names of all known tables, for CLI introspection
        (e.g. a future `structql tables` command) and error messages that
        suggest valid table names."""
        ...
