"""
Tests for the CLI.

Uses Typer's CliRunner to invoke the app the same way a user would from a
terminal - real argument parsing, real exit codes, real stdout/stderr -
rather than calling _run_query directly, so these tests also catch
mistakes in how arguments/options are wired up, not just the query logic
underneath them (which is already covered by test_executor.py).
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from structql.cli import app

runner = CliRunner()


def _write_bridges_fixture(tmp_path: Path) -> tuple[Path, Path]:
    csv_path = tmp_path / "Bridges.csv"
    csv_path.write_text(
        "Name,ConcreteStrength,InspectionDate\n"
        "Jesus Lock Bridge,32MPa,2022\n"
        "Garret Hostel Bridge,40MPa,2024\n",
        encoding="utf-8",
    )
    schema_path = tmp_path / "Bridges.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "table_name": "Bridges",
                "columns": {
                    "Name": "TEXT",
                    "ConcreteStrength": "QUANTITY",
                    "InspectionDate": "NUMBER",
                },
            }
        ),
        encoding="utf-8",
    )
    return csv_path, schema_path


def test_query_command_success(tmp_path: Path) -> None:
    csv_path, schema_path = _write_bridges_fixture(tmp_path)

    result = runner.invoke(
        app,
        [
            "query",
            str(csv_path),
            "SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa",
            "--schema",
            str(schema_path),
        ],
    )

    assert result.exit_code == 0
    assert "Jesus Lock Bridge" in result.stdout
    assert "Garret Hostel Bridge" not in result.stdout
    assert "(1 row)" in result.stdout


def test_query_command_formats_whole_number_floats_without_decimal(tmp_path: Path) -> None:
    csv_path, schema_path = _write_bridges_fixture(tmp_path)

    result = runner.invoke(
        app,
        [
            "query",
            str(csv_path),
            "SELECT InspectionDate FROM Bridges",
            "--schema",
            str(schema_path),
        ],
    )

    assert result.exit_code == 0
    assert "2022" in result.stdout
    assert "2022.0" not in result.stdout


def test_query_command_no_matching_rows(tmp_path: Path) -> None:
    csv_path, schema_path = _write_bridges_fixture(tmp_path)

    result = runner.invoke(
        app,
        [
            "query",
            str(csv_path),
            "SELECT * FROM Bridges WHERE InspectionDate > 2099",
            "--schema",
            str(schema_path),
        ],
    )

    assert result.exit_code == 0
    assert "(0 rows)" in result.stdout


def test_query_command_missing_csv_exits_nonzero_with_clear_error(tmp_path: Path) -> None:
    _, schema_path = _write_bridges_fixture(tmp_path)

    result = runner.invoke(
        app,
        [
            "query",
            str(tmp_path / "does_not_exist.csv"),
            "SELECT * FROM Bridges",
            "--schema",
            str(schema_path),
        ],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_query_command_invalid_query_syntax_exits_nonzero(tmp_path: Path) -> None:
    csv_path, schema_path = _write_bridges_fixture(tmp_path)

    result = runner.invoke(
        app,
        ["query", str(csv_path), "SELECT FROM Bridges", "--schema", str(schema_path)],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_query_command_unknown_column_exits_nonzero(tmp_path: Path) -> None:
    csv_path, schema_path = _write_bridges_fixture(tmp_path)

    result = runner.invoke(
        app,
        [
            "query",
            str(csv_path),
            "SELECT * FROM Bridges WHERE Depth > 20m",
            "--schema",
            str(schema_path),
        ],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
