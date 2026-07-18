"""
Chart export: turns a QueryResult into a saved chart image.

Depends only on QueryResult (engine/executor.py), not on storage or the
executor's internals - it doesn't care whether the data came from a CSV or
an in-memory table. That keeps charting swappable (a plotly backend later
would be a new module implementing the same export_chart signature)
without touching query logic.

Uses matplotlib's non-interactive "Agg" backend, set at import time,
before pyplot is imported - the CLI runs headless (no display), and Agg
is the backend that works correctly without one. Setting it anywhere
other than "before the first pyplot import" is unreliable, so this
module is deliberately the only place that imports pyplot.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

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

    output_path = Path(output_path)
    try:
        fig.savefig(output_path)
    except OSError as exc:
        raise ChartError(f"Could not save chart to {output_path}: {exc}") from None
    finally:
        # Always close the figure, even on a save failure - matplotlib
        # keeps every open figure in memory until explicitly closed, which
        # leaks across repeated calls (e.g. in a test suite or a long-lived
        # process) if this were skipped.
        plt.close(fig)

    return output_path


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
