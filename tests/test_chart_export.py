"""
Tests for export_chart.

matplotlib's Agg backend (set in chart_export.py before pyplot is
imported) makes these tests run headless with no display - fine for CI.
Tests check that a real, non-empty file gets written rather than
inspecting pixel content, since verifying "is this a correct-looking
chart" is a job for a human, not an assertion.
"""

from pathlib import Path

import pytest

from structql.charts.chart_export import export_chart
from structql.domain.quantity import Quantity
from structql.domain.row import Row
from structql.domain.units import Unit
from structql.engine.executor import QueryResult
from structql.exceptions import ChartError


def _piles_result() -> QueryResult:
    return QueryResult(
        columns=["PileID", "Depth", "CutoffLoad"],
        rows=[
            Row(
                values={
                    "PileID": "P1",
                    "Depth": Quantity(22.0, Unit.M),
                    "CutoffLoad": Quantity(450.0, Unit.KN),
                }
            ),
            Row(
                values={
                    "PileID": "P2",
                    "Depth": Quantity(18.0, Unit.M),
                    "CutoffLoad": Quantity(380.0, Unit.KN),
                }
            ),
        ],
    )


def test_export_chart_writes_a_nonempty_file(tmp_path: Path) -> None:
    output = tmp_path / "chart.png"
    returned_path = export_chart(_piles_result(), "Depth", "CutoffLoad", output)

    assert returned_path == output
    assert output.exists()
    assert output.stat().st_size > 0


def test_export_chart_missing_column_raises_chart_error(tmp_path: Path) -> None:
    with pytest.raises(ChartError, match="not in the query result"):
        export_chart(_piles_result(), "Depth", "NotAColumn", tmp_path / "chart.png")


def test_export_chart_text_column_raises_chart_error(tmp_path: Path) -> None:
    with pytest.raises(ChartError, match="text values"):
        export_chart(_piles_result(), "PileID", "CutoffLoad", tmp_path / "chart.png")


def test_export_chart_mixed_units_raises_chart_error(tmp_path: Path) -> None:
    result = QueryResult(
        columns=["CutoffLoad", "Depth"],
        rows=[
            Row(values={"CutoffLoad": Quantity(450.0, Unit.KN), "Depth": Quantity(22.0, Unit.M)}),
            Row(values={"CutoffLoad": Quantity(380.0, Unit.KN), "Depth": Quantity(500.0, Unit.MM)}),
        ],
    )
    with pytest.raises(ChartError, match="mixes units"):
        export_chart(result, "CutoffLoad", "Depth", tmp_path / "chart.png")


def test_export_chart_empty_result_raises_chart_error(tmp_path: Path) -> None:
    result = QueryResult(columns=["Depth", "CutoffLoad"], rows=[])
    with pytest.raises(ChartError, match="empty query result"):
        export_chart(result, "Depth", "CutoffLoad", tmp_path / "chart.png")


def test_export_chart_accepts_custom_title(tmp_path: Path) -> None:
    output = tmp_path / "chart.png"
    export_chart(_piles_result(), "Depth", "CutoffLoad", output, title="Pile Capacity")
    assert output.exists()


def test_render_chart_bytes_returns_valid_png_bytes() -> None:
    from structql.charts.chart_export import render_chart_bytes

    png_bytes = render_chart_bytes(_piles_result(), "Depth", "CutoffLoad")

    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 0
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # PNG file signature


def test_render_chart_bytes_raises_chart_error_same_as_export_chart() -> None:
    from structql.charts.chart_export import render_chart_bytes

    with pytest.raises(ChartError, match="not in the query result"):
        render_chart_bytes(_piles_result(), "Depth", "NotAColumn")
