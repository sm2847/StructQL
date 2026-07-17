"""
AST node definitions - the query's domain model.

These are deliberately plain dataclasses with no behaviour. A
SelectStatement doesn't know how to execute itself; that would couple
parsing to execution and make both harder to test in isolation. The
executor (M6) is the only thing that interprets these nodes.

WHERE-clause conditions form a small expression tree: a Comparison is a
leaf (ConcreteStrength < 35MPa), and BinaryLogic is an internal node
combining two sub-expressions with AND/OR. This mirrors how the parser's
precedence levels nest (see parser.py) - the tree shape IS the precedence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from structql.domain.row import Value


class ComparisonOperator(Enum):
    EQ = "="
    NEQ = "!="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="


class LogicalOperator(Enum):
    AND = "AND"
    OR = "OR"


@dataclass(frozen=True)
class Comparison:
    """A leaf condition, e.g. `ConcreteStrength < 35MPa`."""

    column: str
    operator: ComparisonOperator
    value: Value


@dataclass(frozen=True)
class BinaryLogic:
    """An internal node combining two conditions, e.g. `A AND B`.

    left/right are typed as Expression (the union below) rather than
    specifically Comparison, since either side can itself be a nested
    BinaryLogic - that's what lets `A AND B OR C` form a tree two levels
    deep instead of a flat list.
    """

    left: Expression
    operator: LogicalOperator
    right: Expression


# A WHERE-clause condition is either a single comparison or a combination
# of two conditions. Defined as a type alias (rather than a shared base
# class) so the executor can pattern-match on concrete type with
# isinstance(), which is the clearest way to interpret a small, closed set
# of node types in Python.
Expression = Comparison | BinaryLogic


@dataclass(frozen=True)
class SelectStatement:
    """The root AST node - the whole parsed query.

    columns=["*"] represents SELECT * (STAR can never collide with a real
    column name, so no separate is_star flag is needed).
    """

    columns: list[str]
    table_name: str
    where: Expression | None
