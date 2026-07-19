"""
Tests for the FastAPI app (api/app.py).

Uses Starlette's TestClient (bundled with FastAPI) to send real HTTP
requests - including real multipart file uploads - against the app
in-process. This exercises the exact same code path a browser hitting the
running server would, including FastAPI's request parsing and the
exception handler, not just the underlying pipeline functions (which are
already covered by test_executor.py etc).
"""

import io
import json

from fastapi.testclient import TestClient

from structql.api.app import app

client = TestClient(app)

_BRIDGES_CSV = (
    "Name,ConcreteStrength,InspectionDate\n"
    "Jesus Lock Bridge,32MPa,2024\n"
    "Garret Hostel Bridge,40MPa,2024\n"
    "Coe Fen Footbridge,28MPa,2021\n"
)

_BRIDGES_SCHEMA = json.dumps(
    {
        "table_name": "Bridges",
        "columns": {
            "Name": "TEXT",
            "ConcreteStrength": "QUANTITY",
            "InspectionDate": "NUMBER",
        },
    }
)


def _upload_files():
    return {
        "csv_file": ("Bridges.csv", io.BytesIO(_BRIDGES_CSV.encode("utf-8")), "text/csv"),
        "schema_file": (
            "Bridges.schema.json",
            io.BytesIO(_BRIDGES_SCHEMA.encode("utf-8")),
            "application/json",
        ),
    }


def test_index_serves_html() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "StructQL" in response.text


def test_query_endpoint_returns_filtered_json() -> None:
    where_clause = "ConcreteStrength < 35MPa AND InspectionDate > 2023"
    response = client.post(
        "/api/query",
        data={"query": f"SELECT * FROM Bridges WHERE {where_clause}"},
        files=_upload_files(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["Name", "ConcreteStrength", "InspectionDate"]
    assert len(body["rows"]) == 1
    assert body["rows"][0]["Name"] == "Jesus Lock Bridge"


def test_query_endpoint_serializes_quantity_as_structured_object() -> None:
    response = client.post(
        "/api/query",
        data={"query": "SELECT * FROM Bridges WHERE Name = 'Jesus Lock Bridge'"},
        files=_upload_files(),
    )

    body = response.json()
    concrete_strength = body["rows"][0]["ConcreteStrength"]
    assert concrete_strength == {"value": 32.0, "unit": "MPa"}


def test_query_endpoint_invalid_query_returns_400_with_error_message() -> None:
    response = client.post(
        "/api/query",
        data={"query": "SELECT FROM Bridges"},
        files=_upload_files(),
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_query_endpoint_unknown_column_returns_400() -> None:
    response = client.post(
        "/api/query",
        data={"query": "SELECT * FROM Bridges WHERE Depth > 20m"},
        files=_upload_files(),
    )

    assert response.status_code == 400
    assert "no column 'Depth'" in response.json()["error"]


def test_chart_endpoint_returns_png_bytes() -> None:
    response = client.post(
        "/api/chart",
        data={"query": "SELECT * FROM Bridges", "x": "InspectionDate", "y": "ConcreteStrength"},
        files=_upload_files(),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_chart_endpoint_text_axis_returns_400() -> None:
    response = client.post(
        "/api/chart",
        data={"query": "SELECT * FROM Bridges", "x": "Name", "y": "ConcreteStrength"},
        files=_upload_files(),
    )

    assert response.status_code == 400
    assert "text values" in response.json()["error"]


def test_static_files_are_mounted() -> None:
    response = client.get("/static/index.html")
    assert response.status_code == 200
