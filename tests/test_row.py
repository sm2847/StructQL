from structql.domain.quantity import Quantity
from structql.domain.row import Row
from structql.domain.units import Unit


def test_row_get_returns_typed_value() -> None:
    row = Row(
        values={
            "Name": "Jesus Lock Bridge",
            "ConcreteStrength": Quantity(32.0, Unit.MPA),
            "InspectionDate": 2022.0,
        }
    )
    assert row.get("Name") == "Jesus Lock Bridge"
    assert row.get("ConcreteStrength") == Quantity(32.0, Unit.MPA)
    assert row.get("InspectionDate") == 2022.0
