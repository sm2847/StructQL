import pytest

from structql.domain.schema import ColumnType, Schema
from structql.exceptions import SchemaError


def _bridges_schema() -> Schema:
    return Schema(
        table_name="Bridges",
        columns={
            "Name": ColumnType.TEXT,
            "ConcreteStrength": ColumnType.QUANTITY,
            "InspectionDate": ColumnType.NUMBER,
        },
    )


def test_type_of_known_column() -> None:
    schema = _bridges_schema()
    assert schema.type_of("ConcreteStrength") == ColumnType.QUANTITY


def test_type_of_unknown_column_raises_schema_error() -> None:
    schema = _bridges_schema()
    with pytest.raises(SchemaError, match="no column 'Depth'"):
        schema.type_of("Depth")


def test_has_column() -> None:
    schema = _bridges_schema()
    assert schema.has_column("Name") is True
    assert schema.has_column("Depth") is False
