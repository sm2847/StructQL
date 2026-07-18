"""
Command-line interface.

Deliberately thin: this module's only job is argument parsing, error
presentation, and result formatting - wiring together the schema loader,
importer, storage, and executor. No query logic lives here; if you're
tempted to write an if/else about query semantics in this file, it
belongs in engine/executor.py instead.

v1 design constraint (see README): storage is in-memory only, so there is
no separate persistent `import` step - each `query` invocation loads the
CSV fresh, runs the query, and prints the result, all within one process.
A persistent `import` command is natural future work once a file-backed
StorageEngine exists.
"""

from __future__ import annotations

from pathlib import Path

import typer

from structql.charts.chart_export import export_chart
from structql.domain.row import Value
from structql.engine.executor import QueryResult, execute
from structql.exceptions import StructQLError
from structql.importers.csv_importer import import_csv
from structql.importers.schema_loader import load_schema
from structql.parser.parser import parse
from structql.storage.memory import InMemoryStorageEngine

app = typer.Typer(help="StructQL: query structural engineering CSVs like a database.")


@app.callback()
def _main() -> None:
    """StructQL: query structural engineering CSVs like a database.

    Registering this callback - even though it does nothing itself -
    forces Typer to always require an explicit subcommand name (e.g.
    `structql query ...`), rather than silently collapsing to the single
    top-level command it would otherwise do if `query` were the only
    command registered. This was added in M7, before the `chart` command
    (M8) existed, specifically so adding `chart` wouldn't change the
    invocation shape out from under `query`'s existing usage.
    """


@app.command(name="query")
def query_command(
    # noqa B008: typer.Argument()/typer.Option() calls in defaults are the
    # required idiom for Typer's argument declaration - not the "mutable
    # default" footgun Ruff's B008 normally warns about.
    csv_path: Path = typer.Argument(..., help="Path to the CSV file to query."),  # noqa: B008
    query_string: str = typer.Argument(..., help="The StructQL query to run."),  # noqa: B008
    schema_path: Path = typer.Option(  # noqa: B008
        ..., "--schema", "-s", help="Path to a schema JSON file describing the CSV's columns."
    ),
) -> None:
    """Run a StructQL query directly against a CSV file.

    Example:
        structql query Bridges.csv "SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa" \\
            --schema Bridges.schema.json
    """
    try:
        result = _run_query(csv_path, query_string, schema_path)
    except StructQLError as exc:
        # All of our own exceptions inherit StructQLError (exceptions.py) -
        # one except clause here is enough to catch every schema, parse,
        # lex, or storage failure and present it uniformly.
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None

    _print_result(result)


@app.command(name="chart")
def chart_command(
    csv_path: Path = typer.Argument(..., help="Path to the CSV file to query."),  # noqa: B008
    query_string: str = typer.Argument(..., help="The StructQL query to run."),  # noqa: B008
    schema_path: Path = typer.Option(  # noqa: B008
        ..., "--schema", "-s", help="Path to a schema JSON file describing the CSV's columns."
    ),
    x_column: str = typer.Option(..., "--x", help="Column to plot on the X axis."),  # noqa: B008
    y_column: str = typer.Option(..., "--y", help="Column to plot on the Y axis."),  # noqa: B008
    output_path: Path = typer.Option(  # noqa: B008
        Path("chart.png"), "--out", "-o", help="Where to save the chart image."
    ),
) -> None:
    """Run a query and save a scatter chart of two of its columns.

    The X and Y columns are given explicitly via --x/--y rather than
    inferred from SELECT column order - explicit flags don't silently
    break if the SELECT list is ever reordered.

    Example:
        structql chart Piles.csv "SELECT * FROM Piles" --schema Piles.schema.json \\
            --x Depth --y CutoffLoad --out piles.png
    """
    try:
        result = _run_query(csv_path, query_string, schema_path)
        saved_path = export_chart(result, x_column, y_column, output_path)
    except StructQLError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Chart saved to {saved_path}")


def _run_query(csv_path: Path, query_string: str, schema_path: Path) -> QueryResult:
    """The actual import -> store -> parse -> execute pipeline, factored
    out of query_command so it's testable without going through Typer's
    CLI-invocation machinery."""
    schema = load_schema(schema_path)
    rows = import_csv(csv_path, schema)

    storage = InMemoryStorageEngine()
    storage.create_table(schema)
    storage.insert_rows(schema.table_name, rows)

    statement = parse(query_string)
    return execute(statement, storage)


def _print_result(result: QueryResult) -> None:
    """Print a QueryResult as a simple aligned text table.

    No external table-formatting dependency - the alignment logic here is
    a handful of lines and doesn't warrant pulling in a library.
    """
    if not result.rows:
        typer.echo("(0 rows)")
        return

    formatted_rows = [
        [_format_value(row.get(column)) for column in result.columns] for row in result.rows
    ]
    widths = [
        max(len(column), *(len(cell) for cell in column_cells))
        for column, column_cells in zip(
            result.columns, zip(*formatted_rows, strict=True), strict=True
        )
    ]

    typer.echo("  ".join(col.ljust(w) for col, w in zip(result.columns, widths, strict=True)))
    typer.echo("  ".join("-" * w for w in widths))
    for formatted_row in formatted_rows:
        typer.echo("  ".join(cell.ljust(w) for cell, w in zip(formatted_row, widths, strict=True)))

    row_word = "row" if len(result.rows) == 1 else "rows"
    typer.echo(f"({len(result.rows)} {row_word})")


def _format_value(value: Value) -> str:
    """Format a typed cell value for display.

    Whole-number floats (e.g. 2022.0, from a NUMBER column) print as
    "2022" rather than "2022.0" - CSV years/counts read as integers to a
    user even though they're stored as float internally (domain/row.py).
    """
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    return str(value)


if __name__ == "__main__":
    app()
