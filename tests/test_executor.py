"""
Tests for execute().

Most of these tests run the FULL pipeline (CSV -> import -> storage ->
parse -> execute) rather than hand-building AST/Row objects, because the
point of the executor is to be the layer where every previous milestone's
work actually composes together - that composition is exactly what's worth
testing here, on top of the unit-level behaviour already covered in each
layer's own test file.
"""

from pathlib import Path

import pytest

from structql.domain.schema import ColumnType, Schema
from structql.engine.executor import execute
from structql.exceptions import SchemaError, StorageError
from structql.importers.csv_importer import import_csv
from structql.parser.parser import parse
from structql.storage.memory import InMemoryStorageEngine


def _bridges_schema() -> Schema:
    return Schema(
        table_name="Bridges",
        columns={
            "Name": ColumnType.TEXT,
            "ConcreteStrength": ColumnType.QUANTITY,
            "InspectionDate": ColumnType.NUMBER,
        },
    )


def _load_bridges(tmp_path: Path) -> InMemoryStorageEngine:
    csv_path = tmp_path / "Bridges.csv"
    csv_path.write_text(
        "Name,ConcreteStrength,InspectionDate\n"
        "Jesus Lock Bridge,32MPa,2022\n"
        "Garret Hostel Bridge,40MPa,2024\n"
        "Coe Fen Footbridge,28MPa,2021\n",
        encoding="utf-8",
    )
    schema = _bridges_schema()
    storage = InMemoryStorageEngine()
    storage.create_table(schema)
    storage.insert_rows("Bridges", import_csv(csv_path, schema))
    return storage


def _load_piles(tmp_path: Path) -> InMemoryStorageEngine:
    csv_path = tmp_path / "Piles.csv"
    csv_path.write_text(
        "PileID,Depth\nP1,22m\nP2,18m\nP3,25.5m\n",
        encoding="utf-8",
    )
    schema = Schema(
        table_name="Piles", columns={"PileID": ColumnType.TEXT, "Depth": ColumnType.QUANTITY}
    )
    storage = InMemoryStorageEngine()
    storage.create_table(schema)
    storage.insert_rows("Piles", import_csv(csv_path, schema))
    return storage


def test_select_star_returns_all_columns_and_rows(tmp_path: Path) -> None:
    storage = _load_bridges(tmp_path)
    result = execute(parse("SELECT * FROM Bridges"), storage)

    assert result.columns == ["Name", "ConcreteStrength", "InspectionDate"]
    assert len(result.rows) == 3


def test_select_specific_columns_projects_only_those(tmp_path: Path) -> None:
    storage = _load_bridges(tmp_path)
    result = execute(parse("SELECT Name FROM Bridges"), storage)

    assert result.columns == ["Name"]
    assert all(set(row.values) == {"Name"} for row in result.rows)


def test_original_spec_bridges_query_filters_correctly(tmp_path: Path) -> None:
    storage = _load_bridges(tmp_path)
    source = "SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa AND InspectionDate > 2021"
    result = execute(parse(source), storage)

    names = {row.get("Name") for row in result.rows}
    # Jesus Lock (32MPa, 2022) matches; Garret Hostel (40MPa) fails <35MPa;
    # Coe Fen (28MPa, 2021) fails >2021.
    assert names == {"Jesus Lock Bridge"}


def test_original_spec_piles_query_filters_correctly(tmp_path: Path) -> None:
    storage = _load_piles(tmp_path)
    result = execute(parse("SELECT * FROM Piles WHERE Depth > 20m"), storage)

    ids = {row.get("PileID") for row in result.rows}
    assert ids == {"P1", "P3"}  # P2 is 18m, excluded


def test_or_condition(tmp_path: Path) -> None:
    storage = _load_bridges(tmp_path)
    result = execute(
        parse("SELECT Name FROM Bridges WHERE InspectionDate = 2021 OR InspectionDate = 2024"),
        storage,
    )
    names = {row.get("Name") for row in result.rows}
    assert names == {"Coe Fen Footbridge", "Garret Hostel Bridge"}


def test_unknown_table_raises_storage_error(tmp_path: Path) -> None:
    storage = _load_bridges(tmp_path)
    with pytest.raises(StorageError, match="does not exist"):
        execute(parse("SELECT * FROM Piles"), storage)


def test_unknown_select_column_raises_schema_error(tmp_path: Path) -> None:
    storage = _load_bridges(tmp_path)
    with pytest.raises(SchemaError, match="no column 'Depth'"):
        execute(parse("SELECT Depth FROM Bridges"), storage)


def test_unknown_where_column_raises_schema_error(tmp_path: Path) -> None:
    storage = _load_bridges(tmp_path)
    with pytest.raises(SchemaError, match="no column 'Depth'"):
        execute(parse("SELECT * FROM Bridges WHERE Depth > 20m"), storage)


def test_incompatible_units_in_where_clause_raises(tmp_path: Path) -> None:
    # ConcreteStrength is a PRESSURE column; comparing it against a LENGTH
    # literal should surface the same IncompatibleUnitsError Quantity
    # itself raises (M1) - the executor doesn't swallow or reword it.
    from structql.exceptions import IncompatibleUnitsError

    storage = _load_bridges(tmp_path)
    with pytest.raises(IncompatibleUnitsError):
        execute(parse("SELECT * FROM Bridges WHERE ConcreteStrength < 20m"), storage)


def test_comparing_text_column_with_number_literal_raises_schema_error(
    tmp_path: Path,
) -> None:
    storage = _load_bridges(tmp_path)
    with pytest.raises(SchemaError, match="Cannot compare column 'Name'"):
        execute(parse("SELECT * FROM Bridges WHERE Name > 5"), storage)


def test_no_matching_rows_returns_empty_result(tmp_path: Path) -> None:
    storage = _load_bridges(tmp_path)
    result = execute(parse("SELECT * FROM Bridges WHERE InspectionDate > 2099"), storage)
    assert result.rows == []
    assert result.columns == ["Name", "ConcreteStrength", "InspectionDate"]


@pytest.mark.parametrize(
    ("query_suffix", "expected_names"),
    [
        ("InspectionDate != 2022", {"Garret Hostel Bridge", "Coe Fen Footbridge"}),
        ("InspectionDate <= 2022", {"Jesus Lock Bridge", "Coe Fen Footbridge"}),
        ("InspectionDate >= 2022", {"Jesus Lock Bridge", "Garret Hostel Bridge"}),
    ],
)
def test_all_comparison_operators_through_executor(
    tmp_path: Path, query_suffix: str, expected_names: set[str]
) -> None:
    storage = _load_bridges(tmp_path)
    result = execute(parse(f"SELECT Name FROM Bridges WHERE {query_suffix}"), storage)
    assert {row.get("Name") for row in result.rows} == expected_names
