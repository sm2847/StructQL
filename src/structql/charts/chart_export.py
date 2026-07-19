"""
Chart export: turns a QueryResult into a saved chart image, on disk or as
in-memory bytes.

Depends only on QueryResult (engine/executor.py), not on storage or the
executor's internals - it doesn't care whether the data came from a CSV or
an in-memory table. That keeps charting swappable (a plotly backend later
would be a new module implementing the same signatures) without touching
query logic.

Uses matplotlib's non-interactive "Agg" backend, set at import time,
before pyplot is imported - both the CLI and the FastAPI server (M10) run
headless (no display), and Agg is the backend that works correctly
without one. Setting it anywhere other than "before the first pyplot
import" is unreliable, so this module is deliberately the only place that
imports pyplot.

export_chart (saves to a path) and render_chart_bytes (returns PNG bytes,
for the API to stream in an HTTP response) both delegate to _build_figure
- the actual charting logic exists in exactly one place, regardless of
where the result ends up.
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib
from matplotlib.figure import Figure

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402 - must follow matplotlib.use()

from structql.domain.quantity import Quantity
from structql.domain.row import Value
from structql.engine.executor import QueryResult
from structql.exceptions import ChartError


def export_chart(
    result: QueryResult,
    x_column: str,
    y_column: str,
    output_path: str | Path,
    title: str | None = None,
) -> Path:
    """Render a scatter chart of `y_column` against `x_column` from a
    QueryResult and save it to `output_path`.

    Raises ChartError if either column is missing from the result, holds
    non-numeric (TEXT) values, mixes incompatible units within itself, or
    the result has no rows to plot.
    """
    fig = _build_figure(result, x_column, y_column, title)

    output_path = Path(output_path)
    try:
        fig.savefig(output_path)
    except OSError as exc:
        raise ChartError(f"Could not save chart to {output_path}: {exc}") from None
    finally:
        plt.close(fig)

    return output_path


def render_chart_bytes(
    result: QueryResult,
    x_column: str,
    y_column: str,
    title: str | None = None,
) -> bytes:
    """Render the same chart as export_chart, but return PNG bytes instead
    of writing to disk - used by the FastAPI /api/chart endpoint (M10) to
    stream an image directly in an HTTP response, with no temp file."""
    fig = _build_figure(result, x_column, y_column, title)
    buffer = io.BytesIO()
    try:
        fig.savefig(buffer, format="png")
    finally:
        plt.close(fig)
    return buffer.getvalue()


def _build_figure(result: QueryResult, x_column: str, y_column: str, title: str | None) -> Figure:
    """Shared charting logic: validate, extract numeric values, build the
    figure. Caller owns saving the result AND closing the figure - kept
    that way (rather than closing here) so a save failure in export_chart
    can still be caught before the figure is released."""
    if not result.rows:
        raise ChartError("Cannot chart an empty query result (0 rows) - broaden the query first.")

    _require_column(result, x_column)
    _require_column(result, y_column)

    x_values, x_unit = _numeric_values(result, x_column)
    y_values, y_unit = _numeric_values(result, y_column)

    fig, ax = plt.subplots()
    ax.scatter(x_values, y_values)
    ax.set_xlabel(_axis_label(x_column, x_unit))
    ax.set_ylabel(_axis_label(y_column, y_unit))
    ax.set_title(title or f"{y_column} vs {x_column}")
    fig.tight_layout()
    return fig


def _require_column(result: QueryResult, column: str) -> None:
    if column not in result.columns:
        raise ChartError(
            f"Column '{column}' is not in the query result. "
            f"Available columns: {', '.join(result.columns)}. "
            f"Make sure it's included in your SELECT list."
        )


def _numeric_values(result: QueryResult, column: str) -> tuple[list[float], str | None]:
    """Extract plottable numbers from one column, and its unit label if
    every value shares the same Unit.

    Raises ChartError on a TEXT column (nothing sensible to plot) or on a
    QUANTITY column whose rows don't all share the same unit (see module
    docstring - this is the "don't silently plot mismatched scales"
    check).
    """
    values: list[float] = []
    unit_label: str | None = None

    for row in result.rows:
        cell: Value = row.get(column)

        if isinstance(cell, Quantity):
            if unit_label is None:
                unit_label = cell.unit.value
            elif unit_label != cell.unit.value:
                raise ChartError(
                    f"Column '{column}' mixes units ({unit_label} and {cell.unit.value}) "
                    f"across rows - charting requires a consistent unit, since values "
                    f"aren't auto-converted (see README Future Work)."
                )
            values.append(cell.value)
        elif isinstance(cell, float):
            values.append(cell)
        else:
            raise ChartError(
                f"Column '{column}' contains text values and can't be charted "
                f"on a numeric axis."
            )

    return values, unit_label


def _axis_label(column: str, unit: str | None) -> str:
    return f"{column} ({unit})" if unit else column
