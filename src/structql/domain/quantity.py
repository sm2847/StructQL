"""
Quantity: a numeric value paired with a Unit (e.g. 35MPa, 20m).

This is the type that makes StructQL more than "SQL with extra parsing" -
a Quantity knows how to compare itself against another Quantity, and refuses
to do so when the comparison would be physically meaningless. That logic
lives here (on the type) rather than in the executor, because "how do two
quantities compare" is a property of quantities, not of whoever is asking.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering

from structql.domain.units import Unit, dimension_of
from structql.exceptions import IncompatibleUnitsError


@total_ordering  # generates <=, >, >= from __eq__ and __lt__ below
@dataclass(frozen=True)  # frozen: a Quantity is a value, not a mutable object
class Quantity:
    value: float
    unit: Unit

    def __repr__(self) -> str:  # pragma: no cover - cosmetic only
        return f"{self.value}{self.unit.value}"

    def _check_comparable(self, other: object) -> Quantity:
        """
        Validate that `other` is a Quantity we can meaningfully order against
        `self`, raising a specific, user-facing error if not. Returns `other`
        (typed as Quantity) so call sites don't need a redundant cast.
        """
        if not isinstance(other, Quantity):
            raise TypeError(f"Cannot compare Quantity with {type(other).__name__}")

        if self.unit == other.unit:
            return other

        if dimension_of(self.unit) == dimension_of(other.unit):
            # Same dimension, different unit (e.g. 20mm vs 20m). We deliberately
            # don't auto-convert in v1 (see README "Future Work") - raising here
            # is safer than silently comparing raw numbers in different scales.
            raise IncompatibleUnitsError(
                f"Cannot compare {self.unit.value} with {other.unit.value} directly: "
                f"unit conversion is not yet supported (see README Future Work)."
            )

        raise IncompatibleUnitsError(
            f"Cannot compare {self.unit.value} ({dimension_of(self.unit).value}) "
            f"with {other.unit.value} ({dimension_of(other.unit).value}): "
            f"these measure different physical quantities."
        )

    def __eq__(self, other: object) -> bool:
        # Equality is deliberately lenient: two Quantities of different
        # dimensions are simply not equal, not an error - only *ordering*
        # (<, >, etc.) raises, since "is 35MPa bigger than 20m" is the
        # nonsensical question, while "is 35MPa equal to 20m" has an
        # obvious, safe answer: no.
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.unit == other.unit and self.value == other.value

    def __lt__(self, other: object) -> bool:
        other_q = self._check_comparable(other)
        return self.value < other_q.value

    def __hash__(self) -> int:
        return hash((self.value, self.unit))
