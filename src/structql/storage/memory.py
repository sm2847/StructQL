"""
In-memory implementation of StorageEngine.

This is the default storage for v1 (fine at the data scale a consulting
dataset like "every bridge in a portfolio" implies), and it's the
implementation every other layer's tests run against - fast, no disk
cleanup, no fixtures beyond a plain constructor call.

A future FileStorageEngine (storage/file_storage.py) would satisfy the
same StorageEngine Protocol and could replace this in the CLI/executor
wiring with a one-line change, precisely because nothing outside this
file knows or cares that data currently lives in a dict.
"""

from __future__ import annotations

from structql.domain.row import Row
from structql.domain.schema import Schema
from structql.exceptions import StorageError


class InMemoryStorageEngine:
    def __init__(self) -> None:
        # Two parallel dicts rather than one dict of (schema, rows) tuples:
        # keeps each lookup's intent obvious at the call site
        # (self._schemas[name] vs self._rows[name]) rather than unpacking
        # a tuple every time.
        self._schemas: dict[str, Schema] = {}
        self._rows: dict[str, list[Row]] = {}

    def create_table(self, schema: Schema) -> None:
        if schema.table_name in self._schemas:
            raise StorageError(f"Table '{schema.table_name}' already exists")
        self._schemas[schema.table_name] = schema
        self._rows[schema.table_name] = []

    def insert_rows(self, table_name: str, rows: list[Row]) -> None:
        self._require_table(table_name)
        self._rows[table_name].extend(rows)

    def scan_rows(self, table_name: str) -> list[Row]:
        self._require_table(table_name)
        # Return a copy so callers can't mutate our internal list by
        # accident (e.g. `storage.scan_rows("Bridges").clear()` should not
        # be able to wipe the table).
        return list(self._rows[table_name])

    def get_schema(self, table_name: str) -> Schema:
        self._require_table(table_name)
        return self._schemas[table_name]

    def list_tables(self) -> list[str]:
        return list(self._schemas)

    def _require_table(self, table_name: str) -> None:
        if table_name not in self._schemas:
            known = ", ".join(self._schemas) or "(none)"
            raise StorageError(f"Table '{table_name}' does not exist. Known tables: {known}")
