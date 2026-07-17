"""
Tests for Quantity.

These tests exist to lock in the M1 design decision: comparisons between
compatible units work normally, comparisons across dimensions raise a clear
error instead of silently succeeding, and comparisons within a dimension but
across different units also raise (since v1 doesn't do unit conversion).
"""

import pytest

from structql.domain.quantity import Quantity
from structql.domain.units import Unit
from structql.exceptions import IncompatibleUnitsError


def test_equal_quantities_are_equal() -> None:
    assert Quantity(35.0, Unit.MPA) == Quantity(35.0, Unit.MPA)


def test_different_values_are_not_equal() -> None:
    assert Quantity(35.0, Unit.MPA) != Quantity(40.0, Unit.MPA)


def test_different_dimensions_are_not_equal_but_do_not_raise() -> None:
    # Equality is lenient by design: comparing a pressure to a length is a
    # well-defined "no", not an error.
    assert Quantity(35.0, Unit.MPA) != Quantity(35.0, Unit.M)


def test_ordering_within_same_unit() -> None:
    assert Quantity(30.0, Unit.MPA) < Quantity(35.0, Unit.MPA)
    assert Quantity(35.0, Unit.MPA) > Quantity(30.0, Unit.MPA)
    assert Quantity(35.0, Unit.MPA) <= Quantity(35.0, Unit.MPA)
    assert Quantity(35.0, Unit.MPA) >= Quantity(35.0, Unit.MPA)


def test_ordering_across_dimensions_raises() -> None:
    with pytest.raises(IncompatibleUnitsError):
        _ = Quantity(35.0, Unit.MPA) < Quantity(20.0, Unit.M)


def test_ordering_within_dimension_but_different_unit_raises() -> None:
    # m and mm are both LENGTH, but v1 doesn't auto-convert between them.
    with pytest.raises(IncompatibleUnitsError):
        _ = Quantity(20.0, Unit.M) < Quantity(500.0, Unit.MM)


def test_comparing_against_non_quantity_raises_type_error() -> None:
    with pytest.raises(TypeError):
        _ = Quantity(35.0, Unit.MPA) < 35.0


def test_quantity_repr_round_trips_readably() -> None:
    assert repr(Quantity(35.0, Unit.MPA)) == "35.0MPa"
