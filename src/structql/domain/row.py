"""
Row: one record of typed data, keyed by column name.

Values are already-typed Python objects (str, float, or Quantity) by the
time they reach a Row - the CSV importer (Milestone M2) is responsible for
that conversion. Nothing that consumes a Row should ever need to parse a
string itself; that keeps type-conversion logic in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass

from structql.domain.quantity import Quantity

# The set of Python types a cell value can hold once imported. Defined here
# as a type alias so every module that touches row values (executor, charts,
# CLI formatting) refers to the same definition instead of redefining it.
Value = str | float | Quantity


@dataclass(frozen=True)
class Row:
    """One record. `values` maps column name -> typed value."""

    values: dict[str, Value]

    def get(self, column_name: str) -> Value:
        return self.values[column_name]
