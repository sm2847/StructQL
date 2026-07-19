"""
CSV importer: reads CSV text against a declared Schema and produces typed
Row objects.

Design decision: schemas are declared explicitly by the caller, not
inferred from the CSV's contents. Inference is tempting (less to type per
import) but genuinely ambiguous for this domain - a column of "35, 40, 42"
could be a NUMBER column or a QUANTITY column where nobody happened to
write inconsistent units. Silent misclassification here would produce
wrong query results downstream with no error to point at. Explicit schemas
push that ambiguity to import time, where it's cheap to catch and fix.

This module is also where "untyped string from the outside world" becomes
"typed Python value" - exactly once. Nothing downstream (storage, executor,
CLI, charts) ever looks at a raw CSV string again.

Split into import_csv (reads a file path) and import_csv_text (parses
already-in-memory text) so the FastAPI layer (api/app.py, M10) can reuse
the exact same parsing logic for uploaded files without writing them to a
temp file first just to re-read them.
"""

from __future__ import annotations

import csv
from pathlib import Path

from structql.domain.quantity import Quantity
from structql.domain.row import Row, Value
from structql.domain.schema import ColumnType, Schema
from structql.exceptions import SchemaError, StorageError


def import_csv(path: str | Path, schema: Schema) -> list[Row]:
    """
    Read `path` as a CSV file conforming to `schema` and return one Row per
    data line.

    Raises:
        StorageError: the file doesn't exist or can't be read.
        SchemaError: the CSV header doesn't match the schema's columns, or
            a cell's value can't be converted to its column's declared type.
    """
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise StorageError(f"CSV file not found: {path}") from None
    except OSError as exc:
        raise StorageError(f"Could not read CSV file {path}: {exc}") from None

    return import_csv_text(raw_text, schema, source_description=str(path))


def import_csv_text(raw_text: str, schema: Schema, source_description: str = "<csv>") -> list[Row]:
    """
    Parse CSV text already held in memory (e.g. an uploaded file's
    contents) against `schema` and return one Row per data line.

    `source_description` is used only in error messages (e.g. "row 2,
    column 'ConcreteStrength'") - pass a filename if you have one, so
    errors still point somewhere meaningful even without a real path.
    """
    reader = csv.DictReader(raw_text.splitlines())
    _validate_header(reader.fieldnames, schema, source_description)

    rows: list[Row] = []
    # enumerate from 2: row 1 is the header, so the first data row is "row 2"
    # in the same sense a spreadsheet or text editor would show it - this
    # makes error messages point exactly where a user would look.
    for line_number, raw_row in enumerate(reader, start=2):
        typed_values: dict[str, Value] = {}
        for column_name, column_type in schema.columns.items():
            raw_cell = raw_row[column_name]
            typed_values[column_name] = _convert_cell(
                raw_cell, column_type, column_name, line_number, source_description
            )
        rows.append(Row(values=typed_values))

    return rows


def _validate_header(fieldnames: list[str] | None, schema: Schema, source: str) -> None:
    """Fail fast on a header mismatch rather than importing partial/misaligned
    data - a missing or extra column is almost certainly a mistake worth
    surfacing immediately, not something to silently work around."""
    actual = set(fieldnames or [])
    expected = set(schema.columns)

    missing = expected - actual
    if missing:
        raise SchemaError(
            f"{source}: CSV is missing column(s) required by schema "
            f"'{schema.table_name}': {', '.join(sorted(missing))}"
        )

    unexpected = actual - expected
    if unexpected:
        raise SchemaError(
            f"{source}: CSV has column(s) not declared in schema "
            f"'{schema.table_name}': {', '.join(sorted(unexpected))}"
        )


def _convert_cell(
    raw: str,
    column_type: ColumnType,
    column_name: str,
    line_number: int,
    source: str,
) -> Value:
    """Convert one CSV cell to its declared type, wrapping low-level parse
    errors with enough context (source, row, column) to actually act on."""
    try:
        if column_type is ColumnType.TEXT:
            return raw.strip()
        if column_type is ColumnType.NUMBER:
            return float(raw.strip())
        if column_type is ColumnType.QUANTITY:
            return Quantity.parse(raw)
    except ValueError as exc:
        raise SchemaError(f"{source}, row {line_number}, column '{column_name}': {exc}") from None

    # Unreachable while ColumnType only has the three members above, but
    # keeps this function honest if a new ColumnType is ever added without
    # updating the converter.
    raise SchemaError(f"Unhandled column type {column_type} for column '{column_name}'")
