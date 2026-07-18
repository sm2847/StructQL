"""
Schema loader: reads a table's Schema from a small companion JSON file.

Example schema file (Bridges.schema.json):
{
  "table_name": "Bridges",
  "columns": {
    "Name": "TEXT",
    "ConcreteStrength": "QUANTITY",
    "InspectionDate": "NUMBER"
  }
}

Design decision: schemas are declared in a file, not as repeated CLI flags
(e.g. --column Name:TEXT --column ConcreteStrength:QUANTITY ...). Flags are
more explicit with zero extra files, but get unwieldy past a handful of
columns and don't scale to a real engineering dataset with a dozen fields.
A schema file also becomes a second real, committable artifact describing
a dataset - documentation of what the data IS, not just how to query it.
"""

from __future__ import annotations

import json
from pathlib import Path

from structql.domain.schema import ColumnType, Schema
from structql.exceptions import SchemaError


def load_schema(path: str | Path) -> Schema:
    """Load and validate a Schema from a JSON file.

    Raises SchemaError for any failure mode: missing file, invalid JSON,
    missing required keys, or an unrecognised column type - all as the
    same exception type the rest of the codebase already uses for schema
    problems, so callers (the CLI) only need one except clause.
    """
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SchemaError(f"Schema file not found: {path}") from None
    except OSError as exc:
        raise SchemaError(f"Could not read schema file {path}: {exc}") from None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"Schema file {path} is not valid JSON: {exc}") from None

    try:
        table_name = data["table_name"]
        raw_columns = data["columns"]
    except KeyError as exc:
        raise SchemaError(f"Schema file {path} is missing required key: {exc}") from None
    except TypeError:
        raise SchemaError(
            f"Schema file {path} must contain a JSON object with 'table_name' and 'columns'"
        ) from None

    columns: dict[str, ColumnType] = {}
    for column_name, type_text in raw_columns.items():
        try:
            columns[column_name] = ColumnType(type_text)
        except ValueError:
            known = ", ".join(t.value for t in ColumnType)
            raise SchemaError(
                f"Schema file {path}, column '{column_name}': unrecognised type "
                f"'{type_text}' (expected one of: {known})"
            ) from None

    return Schema(table_name=table_name, columns=columns)
