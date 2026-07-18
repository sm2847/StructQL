"""
Executor: runs a parsed SelectStatement against a StorageEngine and
produces a QueryResult.

This is the business-logic layer, and the only place unit-aware WHERE
evaluation happens (via Quantity's own comparison operators from M1) - the
parser doesn't evaluate anything, and storage doesn't know what a WHERE
clause is. The executor depends on StorageEngine as an interface (M3), so
it's tested here against InMemoryStorageEngine with zero disk I/O.

Two things are validated up front, before any row is scanned or filtered:
  1. The table exists (via storage.get_schema, which raises if not).
  2. Every column referenced - in SELECT and in WHERE - exists in the
     schema.
Failing fast here means a typo'd column name on a 10,000-row table is a
single clear error, not a wasted full scan followed by a KeyError deep in
row projection.
"""

from __future__ import annotations

from dataclasses import dataclass

from structql.domain.row import Row
from structql.domain.schema import Schema
from structql.exceptions import SchemaError
from structql.parser.ast_nodes import (
    Comparison,
    ComparisonOperator,
    Expression,
    LogicalOperator,
    SelectStatement,
)
from structql.storage.base import StorageEngine


@dataclass(frozen=True)
class QueryResult:
    """The output of running a query: the columns actually selected (in
    the order requested), and the matching rows projected down to just
    those columns.

    Deliberately a plain data holder with no methods - the CLI (M7) and
    charts (M8) both consume this directly, and neither should need to
    reach back into the executor or storage to do so.
    """

    columns: list[str]
    rows: list[Row]


def execute(statement: SelectStatement, storage: StorageEngine) -> QueryResult:
    """Run a parsed query against storage and return its result."""
    schema = storage.get_schema(statement.table_name)  # raises StorageError if unknown table
    resolved_columns = _resolve_columns(statement.columns, schema)

    if statement.where is not None:
        _validate_where_columns(statement.where, schema)

    rows = storage.scan_rows(statement.table_name)
    if statement.where is not None:
        rows = [row for row in rows if _evaluate(statement.where, row)]

    projected = [Row(values={col: row.get(col) for col in resolved_columns}) for row in rows]
    return QueryResult(columns=resolved_columns, rows=projected)


def _resolve_columns(columns: list[str], schema: Schema) -> list[str]:
    """Expand SELECT * to the schema's full column list (in schema order),
    or validate that every explicitly-named column exists."""
    if columns == ["*"]:
        return list(schema.columns)

    for column in columns:
        schema.type_of(column)  # raises SchemaError with a helpful message if missing
    return columns


def _validate_where_columns(expr: Expression, schema: Schema) -> None:
    """Walk the WHERE expression tree and confirm every referenced column
    exists, before scanning a single row. Mirrors the recursive shape of
    _evaluate below - this function only checks existence, _evaluate does
    the actual filtering."""
    if isinstance(expr, Comparison):
        schema.type_of(expr.column)
    else:
        _validate_where_columns(expr.left, schema)
        _validate_where_columns(expr.right, schema)


def _evaluate(expr: Expression, row: Row) -> bool:
    """Recursively evaluate a WHERE expression against one row.

    Mirrors how the parser BUILT this tree (_parse_or/_parse_and/
    _parse_comparison) - here we walk it instead. Python's `and`/`or`
    below short-circuit natively, so `A AND B` never evaluates B once A is
    False, matching standard boolean-logic semantics.
    """
    if isinstance(expr, Comparison):
        return _evaluate_comparison(expr, row)

    if expr.operator is LogicalOperator.AND:
        return _evaluate(expr.left, row) and _evaluate(expr.right, row)
    return _evaluate(expr.left, row) or _evaluate(expr.right, row)


def _evaluate_comparison(comparison: Comparison, row: Row) -> bool:
    """Evaluate one leaf comparison, e.g. ConcreteStrength < 35MPa.

    Relies on Quantity's own __eq__/__lt__ etc. (M1) for unit-aware
    comparisons - IncompatibleUnitsError from a nonsensical unit
    comparison propagates up as-is, since it's already a clear, specific
    error. A generic type mismatch (e.g. comparing a TEXT column with a
    NUMBER literal) raises a plain TypeError from Python itself, which we
    catch and wrap with column context to make it actionable.
    """
    actual = row.get(comparison.column)
    expected = comparison.value
    op = comparison.operator

    try:
        if op is ComparisonOperator.EQ:
            return actual == expected
        if op is ComparisonOperator.NEQ:
            return actual != expected
        if op is ComparisonOperator.LT:
            return actual < expected  # type: ignore[operator]
        if op is ComparisonOperator.GT:
            return actual > expected  # type: ignore[operator]
        if op is ComparisonOperator.LE:
            return actual <= expected  # type: ignore[operator]
        if op is ComparisonOperator.GE:
            return actual >= expected  # type: ignore[operator]
    except TypeError as exc:
        raise SchemaError(
            f"Cannot compare column '{comparison.column}' "
            f"({type(actual).__name__} value {actual!r}) with "
            f"{type(expected).__name__} value {expected!r}: {exc}"
        ) from None

    raise AssertionError(f"Unhandled comparison operator: {op}")  # pragma: no cover
