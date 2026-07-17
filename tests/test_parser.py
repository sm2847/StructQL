"""
Tests for parse().

The precedence tests are the most important ones here: they lock in that
`A AND B OR C` produces (A AND B) OR C as a tree, not a flat list or the
opposite grouping - that's the entire point of the recursive-descent
structure in parser.py.
"""

import pytest

from structql.domain.quantity import Quantity
from structql.domain.units import Unit
from structql.exceptions import ParserError
from structql.parser.ast_nodes import (
    BinaryLogic,
    Comparison,
    ComparisonOperator,
    LogicalOperator,
    SelectStatement,
)
from structql.parser.parser import parse


def test_select_star_no_where() -> None:
    stmt = parse("SELECT * FROM Bridges")
    assert stmt == SelectStatement(columns=["*"], table_name="Bridges", where=None)


def test_select_column_list() -> None:
    stmt = parse("SELECT Name, ConcreteStrength FROM Bridges")
    assert stmt.columns == ["Name", "ConcreteStrength"]
    assert stmt.table_name == "Bridges"


def test_single_comparison_with_quantity() -> None:
    stmt = parse("SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa")
    assert stmt.where == Comparison(
        column="ConcreteStrength",
        operator=ComparisonOperator.LT,
        value=Quantity(35.0, Unit.MPA),
    )


def test_single_comparison_with_number() -> None:
    stmt = parse("SELECT * FROM Bridges WHERE InspectionDate > 2023")
    assert stmt.where == Comparison(
        column="InspectionDate", operator=ComparisonOperator.GT, value=2023.0
    )


def test_single_comparison_with_string() -> None:
    stmt = parse("SELECT * FROM Bridges WHERE Name = 'Jesus Lock Bridge'")
    assert stmt.where == Comparison(
        column="Name", operator=ComparisonOperator.EQ, value="Jesus Lock Bridge"
    )


def test_all_comparison_operators_parse() -> None:
    for op_text, op_enum in [
        ("=", ComparisonOperator.EQ),
        ("!=", ComparisonOperator.NEQ),
        ("<", ComparisonOperator.LT),
        (">", ComparisonOperator.GT),
        ("<=", ComparisonOperator.LE),
        (">=", ComparisonOperator.GE),
    ]:
        stmt = parse(f"SELECT * FROM Bridges WHERE InspectionDate {op_text} 2023")
        assert stmt.where.operator == op_enum  # type: ignore[union-attr]


def test_simple_and() -> None:
    stmt = parse("SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa AND InspectionDate > 2023")
    assert stmt.where == BinaryLogic(
        left=Comparison(
            column="ConcreteStrength",
            operator=ComparisonOperator.LT,
            value=Quantity(35.0, Unit.MPA),
        ),
        operator=LogicalOperator.AND,
        right=Comparison(column="InspectionDate", operator=ComparisonOperator.GT, value=2023.0),
    )


def test_simple_or() -> None:
    stmt = parse("SELECT * FROM Bridges WHERE InspectionDate > 2023 OR InspectionDate = 2020")
    assert isinstance(stmt.where, BinaryLogic)
    assert stmt.where.operator == LogicalOperator.OR


def test_and_binds_tighter_than_or() -> None:
    # A AND B OR C  must parse as  (A AND B) OR C
    stmt = parse(
        "SELECT * FROM T WHERE InspectionDate = 1 AND InspectionDate = 2 OR InspectionDate = 3"
    )
    where = stmt.where
    assert isinstance(where, BinaryLogic)
    assert where.operator == LogicalOperator.OR
    assert isinstance(where.left, BinaryLogic)
    assert where.left.operator == LogicalOperator.AND
    assert where.left.left == Comparison("InspectionDate", ComparisonOperator.EQ, 1.0)
    assert where.left.right == Comparison("InspectionDate", ComparisonOperator.EQ, 2.0)
    assert where.right == Comparison("InspectionDate", ComparisonOperator.EQ, 3.0)


def test_or_then_and_still_groups_and_first() -> None:
    # A OR B AND C  must parse as  A OR (B AND C)
    stmt = parse(
        "SELECT * FROM T WHERE InspectionDate = 1 OR InspectionDate = 2 AND InspectionDate = 3"
    )
    where = stmt.where
    assert isinstance(where, BinaryLogic)
    assert where.operator == LogicalOperator.OR
    assert where.left == Comparison("InspectionDate", ComparisonOperator.EQ, 1.0)
    assert isinstance(where.right, BinaryLogic)
    assert where.right.operator == LogicalOperator.AND


def test_missing_from_raises_parser_error() -> None:
    with pytest.raises(ParserError, match="Expected FROM"):
        parse("SELECT * Bridges")


def test_missing_table_name_raises_parser_error() -> None:
    with pytest.raises(ParserError, match="Expected IDENTIFIER"):
        parse("SELECT * FROM")


def test_incomplete_where_raises_parser_error() -> None:
    with pytest.raises(ParserError):
        parse("SELECT * FROM Bridges WHERE ConcreteStrength <")


def test_invalid_comparison_operator_raises_parser_error() -> None:
    with pytest.raises(ParserError, match="Expected a comparison operator"):
        parse("SELECT * FROM Bridges WHERE ConcreteStrength AND 35MPa")


def test_trailing_garbage_after_query_raises_parser_error() -> None:
    with pytest.raises(ParserError, match="Expected EOF"):
        parse("SELECT * FROM Bridges EXTRA")


def test_unknown_unit_in_quantity_literal_raises_parser_error() -> None:
    with pytest.raises(ParserError, match="Invalid quantity"):
        parse("SELECT * FROM Bridges WHERE Depth > 20xyz")


def test_original_spec_example_bridges_query() -> None:
    source = """SELECT *
    FROM Bridges
    WHERE
    ConcreteStrength < 35MPa
    AND
    InspectionDate > 2023"""
    stmt = parse(source)
    assert stmt.columns == ["*"]
    assert stmt.table_name == "Bridges"
    assert isinstance(stmt.where, BinaryLogic)
    assert stmt.where.operator == LogicalOperator.AND


def test_original_spec_example_piles_query() -> None:
    source = """SELECT *
    FROM Piles
    WHERE
    Depth > 20m"""
    stmt = parse(source)
    assert stmt.columns == ["*"]
    assert stmt.table_name == "Piles"
    assert stmt.where == Comparison(
        column="Depth", operator=ComparisonOperator.GT, value=Quantity(20.0, Unit.M)
    )
