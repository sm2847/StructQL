"""
Units of measurement and the physical dimensions they belong to.

Why a separate Dimension concept: "MPa" and "kN" are both units, but they
measure different things (pressure vs. force) and can never be meaningfully
compared. Tagging each Unit with its Dimension lets Quantity (quantity.py)
reject nonsense comparisons like `35MPa < 20m` at comparison time, instead
of silently returning False or crashing further down the pipeline.

Adding a new unit later (e.g. "kPa") means adding one enum member and one
line in _DIMENSIONS - the rest of the system (lexer, parser, executor)
doesn't need to change. That's the Open/Closed Principle in practice.
"""

from __future__ import annotations

from enum import Enum


class Dimension(Enum):
    """What physical quantity a unit measures. Two Quantities can only be
    compared if they share a Dimension."""

    PRESSURE = "pressure"
    FORCE = "force"
    LENGTH = "length"


class Unit(Enum):
    """
    Units recognised by the StructQL lexer inside a quantity literal
    (e.g. the "MPa" in "35MPa").

    The string value is exactly the suffix a user types in a query, so the
    lexer can do `Unit(suffix)` directly without a separate lookup table.
    """

    MPA = "MPa"
    KN = "kN"
    M = "m"
    MM = "mm"


# Single source of truth for "which unit measures what". Kept as a plain
# dict close to the enums it describes, rather than as a method on Unit,
# so the enum definition itself stays purely about *identity* (what units
# exist) and this table stays purely about *meaning* (what they measure).
_DIMENSIONS: dict[Unit, Dimension] = {
    Unit.MPA: Dimension.PRESSURE,
    Unit.KN: Dimension.FORCE,
    Unit.M: Dimension.LENGTH,
    Unit.MM: Dimension.LENGTH,
}


def dimension_of(unit: Unit) -> Dimension:
    """Return the physical dimension a unit measures."""
    return _DIMENSIONS[unit]
