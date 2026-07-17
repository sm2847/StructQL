"""
Tests for InMemoryStorageEngine.

These tests are written against the StorageEngine Protocol's documented
behaviour (base.py), not against InMemoryStorageEngine-specific internals -
if a FileStorageEngine is added later, this same test file (parametrised
over both implementations) should be able to verify it too.
"""

import pytest

from structql.domain.quantity import Quantity
from structql.domain.row import Row
from structql.domain.schema import ColumnType, Schema
from structql.domain.units import Unit
from structql.exceptions import StorageError
from structql.storage.base import StorageEngine
from structql.storage.memory import InMemoryStorageEngine


def _bridges_schema() -> Schema:
    return Schema(
        table_name="Bridges",
        columns={"Name": ColumnType.TEXT, "ConcreteStrength": ColumnType.QUANTITY},
    )


def _sample_row() -> Row:
    return Row(values={"Name": "Jesus Lock Bridge", "ConcreteStrength": Quantity(32.0, Unit.MPA)})


def test_in_memory_storage_satisfies_protocol() -> None:
    # Structural check: InMemoryStorageEngine should count as a
    # StorageEngine without explicitly subclassing it (that's the point
    # of using a Protocol).
    assert isinstance(InMemoryStorageEngine(), StorageEngine)


def test_create_table_registers_schema() -> None:
    storage = InMemoryStorageEngine()
    storage.create_table(_bridges_schema())
    assert storage.get_schema("Bridges").table_name == "Bridges"


def test_create_duplicate_table_raises() -> None:
    storage = InMemoryStorageEngine()
    storage.create_table(_bridges_schema())
    with pytest.raises(StorageError, match="already exists"):
        storage.create_table(_bridges_schema())


def test_insert_and_scan_round_trip() -> None:
    storage = InMemoryStorageEngine()
    storage.create_table(_bridges_schema())
    storage.insert_rows("Bridges", [_sample_row()])

    rows = storage.scan_rows("Bridges")
    assert len(rows) == 1
    assert rows[0].get("Name") == "Jesus Lock Bridge"


def test_scan_rows_preserves_insertion_order() -> None:
    storage = InMemoryStorageEngine()
    storage.create_table(_bridges_schema())
    row_a = Row(values={"Name": "A", "ConcreteStrength": Quantity(30.0, Unit.MPA)})
    row_b = Row(values={"Name": "B", "ConcreteStrength": Quantity(40.0, Unit.MPA)})
    storage.insert_rows("Bridges", [row_a, row_b])

    rows = storage.scan_rows("Bridges")
    assert [r.get("Name") for r in rows] == ["A", "B"]


def test_scan_rows_returns_a_copy_not_internal_list() -> None:
    storage = InMemoryStorageEngine()
    storage.create_table(_bridges_schema())
    storage.insert_rows("Bridges", [_sample_row()])

    rows = storage.scan_rows("Bridges")
    rows.clear()  # mutate the returned list

    # Internal state must be unaffected by mutating the returned list.
    assert len(storage.scan_rows("Bridges")) == 1


def test_insert_into_unknown_table_raises() -> None:
    storage = InMemoryStorageEngine()
    with pytest.raises(StorageError, match="does not exist"):
        storage.insert_rows("Bridges", [_sample_row()])


def test_scan_unknown_table_raises() -> None:
    storage = InMemoryStorageEngine()
    with pytest.raises(StorageError, match="does not exist"):
        storage.scan_rows("Bridges")


def test_get_schema_unknown_table_raises() -> None:
    storage = InMemoryStorageEngine()
    with pytest.raises(StorageError, match="does not exist"):
        storage.get_schema("Bridges")


def test_list_tables() -> None:
    storage = InMemoryStorageEngine()
    assert storage.list_tables() == []
    storage.create_table(_bridges_schema())
    storage.create_table(Schema(table_name="Piles", columns={"PileID": ColumnType.TEXT}))
    assert set(storage.list_tables()) == {"Bridges", "Piles"}
