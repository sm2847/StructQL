"""
FastAPI web layer: exposes the same execute()/render_chart_bytes()
pipeline the CLI (M7/M8) uses, over HTTP, and serves a small static
frontend (static/index.html).

Why a separate api/ package rather than extending cli.py: this is a
different TRANSPORT for the exact same business logic (HTTP request
instead of a terminal invocation), not new business logic. Keeping it as
thin wiring next to - not inside - engine/executor.py and
charts/chart_export.py is the same principle the CLI already follows:
neither cli.py nor api/app.py should ever contain query-evaluation logic
themselves. If this file starts importing structql.lexer or reasoning
about WHERE clauses directly, that's a sign logic has leaked into the
wrong layer.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from structql.charts.chart_export import render_chart_bytes
from structql.domain.quantity import Quantity
from structql.domain.row import Value
from structql.engine.executor import QueryResult, execute
from structql.exceptions import StructQLError
from structql.importers.csv_importer import import_csv_text
from structql.importers.schema_loader import parse_schema
from structql.parser.parser import parse
from structql.storage.memory import InMemoryStorageEngine

app = FastAPI(
    title="StructQL",
    description="Query structural engineering CSVs like a database, over HTTP.",
)

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.exception_handler(StructQLError)
async def handle_structql_error(request: Request, exc: StructQLError) -> JSONResponse:
    """Single place every StructQL-specific failure (schema, parse, lex,
    storage, chart) becomes an HTTP response - the FastAPI-idiomatic
    equivalent of the CLI's one except-StructQLError clause (cli.py). A
    route function below never needs its own try/except for these."""
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.get("/")
async def index() -> Response:
    """Serve the static frontend's entry point at the site root."""
    html_path = _STATIC_DIR / "index.html"
    return Response(content=html_path.read_text(encoding="utf-8"), media_type="text/html")


async def _load_result(
    csv_file: UploadFile, schema_file: UploadFile, query_string: str
) -> QueryResult:
    """Shared pipeline for /api/query and /api/chart: uploaded files ->
    typed rows -> in-memory storage -> parsed query -> QueryResult.

    Mirrors cli._run_query (cli.py), adapted for in-memory uploads instead
    of filesystem paths - this reuse is exactly why import_csv_text and
    parse_schema were split out of import_csv/load_schema: without that
    split, this function would need to write every upload to a temp file
    first just to satisfy a path-shaped function signature.
    """
    schema_text = (await schema_file.read()).decode("utf-8")
    schema = parse_schema(schema_text, source_description=schema_file.filename or "<schema>")

    csv_text = (await csv_file.read()).decode("utf-8")
    rows = import_csv_text(csv_text, schema, source_description=csv_file.filename or "<csv>")

    storage = InMemoryStorageEngine()
    storage.create_table(schema)
    storage.insert_rows(schema.table_name, rows)

    statement = parse(query_string)
    return execute(statement, storage)


@app.post("/api/query")
async def query_endpoint(
    query: str = Form(...),
    csv_file: UploadFile = File(...),  # noqa: B008
    schema_file: UploadFile = File(...),  # noqa: B008
) -> JSONResponse:
    """Run a query against an uploaded CSV + schema, return the result as JSON."""
    result = await _load_result(csv_file, schema_file, query)
    return JSONResponse(
        content={
            "columns": result.columns,
            "rows": [
                {column: _serialize_value(row.get(column)) for column in result.columns}
                for row in result.rows
            ],
        }
    )


@app.post("/api/chart")
async def chart_endpoint(
    query: str = Form(...),
    x: str = Form(...),
    y: str = Form(...),
    csv_file: UploadFile = File(...),  # noqa: B008
    schema_file: UploadFile = File(...),  # noqa: B008
) -> Response:
    """Run a query against an uploaded CSV + schema, return a PNG chart."""
    result = await _load_result(csv_file, schema_file, query)
    png_bytes = render_chart_bytes(result, x, y)
    return Response(content=png_bytes, media_type="image/png")


def _serialize_value(value: Value) -> float | str | dict[str, object]:
    """Convert one typed cell value into something JSON can represent.

    A Quantity becomes a small structured object ({"value": ..., "unit":
    ...}), not just a formatted string like "35.0MPa" - this lets the
    frontend use the numeric value and unit separately (e.g. to sort
    numerically, or label a chart) without re-parsing a display string
    back into its parts.
    """
    if isinstance(value, Quantity):
        return {"value": value.value, "unit": value.unit.value}
    return value
