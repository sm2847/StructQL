"""
Tests for import_csv.

Uses pytest's tmp_path fixture to write real CSV files to a temp directory
per test - this exercises actual file I/O (not a mocked file object), which
matters here since a chunk of this module's job is reading files correctly.
"""

from pathlib import Path

import pytest

from structql.domain.quantity import Quantity
from structql.domain.schema import ColumnType, Schema
from structql.domain.units import Unit
from structql.exceptions import SchemaError, StorageError
from structql.importers.csv_importer import import_csv


def _bridges_schema() -> Schema:
    return Schema(
        table_name="Bridges",
        columns={
            "Name": ColumnType.TEXT,
            "ConcreteStrength": ColumnType.QUANTITY,
            "InspectionDate": ColumnType.NUMBER,
        },
    )


def _write_csv(tmp_path: Path, content: str) -> Path:
    csv_path = tmp_path / "Bridges.csv"
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


def test_import_valid_csv_produces_typed_rows(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "Name,ConcreteStrength,InspectionDate\n"
        "Jesus Lock Bridge,32MPa,2022\n"
        "Garret Hostel Bridge,40MPa,2024\n",
    )

    rows = import_csv(csv_path, _bridges_schema())

    assert len(rows) == 2
    assert rows[0].get("Name") == "Jesus Lock Bridge"
    assert rows[0].get("ConcreteStrength") == Quantity(32.0, Unit.MPA)
    assert rows[0].get("InspectionDate") == 2022.0
    assert rows[1].get("Name") == "Garret Hostel Bridge"


def test_import_missing_column_raises_schema_error(tmp_path: Path) -> None:
    # No InspectionDate column at all.
    csv_path = _write_csv(tmp_path, "Name,ConcreteStrength\nJesus Lock Bridge,32MPa\n")

    with pytest.raises(SchemaError, match="missing column"):
        import_csv(csv_path, _bridges_schema())


def test_import_unexpected_column_raises_schema_error(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "Name,ConcreteStrength,InspectionDate,Architect\n" "Jesus Lock Bridge,32MPa,2022,Someone\n",
    )

    with pytest.raises(SchemaError, match="not declared in schema"):
        import_csv(csv_path, _bridges_schema())


def test_import_malformed_quantity_raises_schema_error_with_location(
    tmp_path: Path,
) -> None:
    csv_path = _write_csv(
        tmp_path,
        "Name,ConcreteStrength,InspectionDate\nJesus Lock Bridge,not-a-quantity,2022\n",
    )

    with pytest.raises(SchemaError, match=r"row 2, column 'ConcreteStrength'"):
        import_csv(csv_path, _bridges_schema())


def test_import_malformed_number_raises_schema_error(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "Name,ConcreteStrength,InspectionDate\nJesus Lock Bridge,32MPa,not-a-year\n",
    )

    with pytest.raises(SchemaError, match="column 'InspectionDate'"):
        import_csv(csv_path, _bridges_schema())


def test_import_missing_file_raises_storage_error(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="not found"):
        import_csv(tmp_path / "does_not_exist.csv", _bridges_schema())
