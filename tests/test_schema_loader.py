import json
from pathlib import Path

import pytest

from structql.domain.schema import ColumnType
from structql.exceptions import SchemaError
from structql.importers.schema_loader import load_schema


def _write_schema(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "Bridges.schema.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_valid_schema(tmp_path: Path) -> None:
    path = _write_schema(
        tmp_path,
        {
            "table_name": "Bridges",
            "columns": {
                "Name": "TEXT",
                "ConcreteStrength": "QUANTITY",
                "InspectionDate": "NUMBER",
            },
        },
    )
    schema = load_schema(path)
    assert schema.table_name == "Bridges"
    assert schema.type_of("ConcreteStrength") == ColumnType.QUANTITY


def test_missing_file_raises_schema_error(tmp_path: Path) -> None:
    with pytest.raises(SchemaError, match="not found"):
        load_schema(tmp_path / "does_not_exist.json")


def test_invalid_json_raises_schema_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(SchemaError, match="not valid JSON"):
        load_schema(path)


def test_missing_table_name_key_raises_schema_error(tmp_path: Path) -> None:
    path = _write_schema(tmp_path, {"columns": {"Name": "TEXT"}})
    with pytest.raises(SchemaError, match="missing required key"):
        load_schema(path)


def test_missing_columns_key_raises_schema_error(tmp_path: Path) -> None:
    path = _write_schema(tmp_path, {"table_name": "Bridges"})
    with pytest.raises(SchemaError, match="missing required key"):
        load_schema(path)


def test_unknown_column_type_raises_schema_error(tmp_path: Path) -> None:
    path = _write_schema(
        tmp_path, {"table_name": "Bridges", "columns": {"Name": "STRING_BUT_WRONG_NAME"}}
    )
    with pytest.raises(SchemaError, match="unrecognised type"):
        load_schema(path)


def test_parse_schema_parses_in_memory_text_directly() -> None:
    # Same underlying logic load_schema uses, but no filesystem touched -
    # exercises the split that lets the API (M10) parse an uploaded schema
    # file's contents without writing it to disk first.
    from structql.importers.schema_loader import parse_schema

    text = json.dumps({"table_name": "Bridges", "columns": {"Name": "TEXT"}})
    schema = parse_schema(text, source_description="upload.schema.json")

    assert schema.table_name == "Bridges"
