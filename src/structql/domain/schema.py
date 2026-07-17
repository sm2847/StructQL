"""
Schema: describes the shape of a table (column names and their types).

Deliberately separate from Row (row.py) - a Schema describes a table once;
a Row is one instance of data conforming to it. Keeping "shape" and "data"
as distinct types means validation (does this value match this column's
type?) has an obvious home: schema.py, not scattered through the importer
or executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from structql.exceptions import SchemaError


class ColumnType(Enum):
    """
    The type a column holds.

    QUANTITY covers any unit-bearing value (e.g. "35MPa", "20m") - the
    specific Unit is carried by each individual Quantity value, not fixed
    per-column, since a column like Depth might reasonably hold both `20m`
    and `500mm` entries in real-world CSV data.
    """

    TEXT = "TEXT"
    NUMBER = "NUMBER"
    QUANTITY = "QUANTITY"


@dataclass(frozen=True)
class Schema:
    """A table's column definitions, in declaration order."""

    table_name: str
    columns: dict[str, ColumnType]

    def type_of(self, column_name: str) -> ColumnType:
        """Look up a column's type, raising a clear error if it doesn't exist.

        Centralising this lookup (rather than letting callers do
        `schema.columns[name]` directly) means every "unknown column" error
        message is consistent, wherever it's triggered from.
        """
        try:
            return self.columns[column_name]
        except KeyError:
            raise SchemaError(
                f"Table '{self.table_name}' has no column '{column_name}'. "
                f"Available columns: {', '.join(self.columns)}"
            ) from None

    def has_column(self, column_name: str) -> bool:
        return column_name in self.columns
