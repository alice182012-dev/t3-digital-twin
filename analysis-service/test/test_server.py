"""GET /health of the analysis service, without a database.

    python3 -m pytest analysis-service/test

A real HTTP client calls the real Handler. The connection is a fake that answers the manifest query.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import psycopg2

SERVICE = Path(__file__).resolve().parents[1]
REPO = SERVICE.parent
sys.path.insert(0, str(SERVICE / "app"))

import server  # noqa: E402


def _load_run_output():
    spec = importlib.util.spec_from_file_location("run_output", REPO / "scripts" / "database" / "run_output.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.executed.append((sql, params))

    def fetchone(self):
        return self.conn.row


class FakeConnection:
    def __init__(self, row):
        self.row = row
        self.executed = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


def test_the_core_outputs_are_the_values_of_run_output_output():
    run_output = _load_run_output()

    assert server.CORE_OUTPUTS == {output.value for output in run_output.Output}


def test_the_query_asks_for_the_four_outputs_and_returns_the_run_ts():
    conn = FakeConnection(("20261011T001500",))

    assert server.newest_complete_run(conn) == "20261011T001500"
    assert conn.executed[0][1] == {"outputs": ["depth_raster", "edge_depth", "extent", "road_values"]}


def test_the_query_returns_none_when_no_run_has_all_four():
    assert server.newest_complete_run(FakeConnection(None)) is None


def _get(path: str, connect) -> tuple[int, dict]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with patch.object(server, "connect", connect):
            url = f"http://127.0.0.1:{httpd.server_address[1]}{path}"
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    return response.status, json.loads(response.read())
            except urllib.error.HTTPError as error:
                return error.code, json.loads(error.read())
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_health_returns_the_newest_complete_run_and_closes_the_connection():
    conn = FakeConnection(("20261011T001500",))

    assert _get("/health", lambda: conn) == (200, {"run_ts": "20261011T001500"})
    assert conn.closed


def test_health_returns_null_when_no_run_is_complete():
    assert _get("/health", lambda: FakeConnection(None)) == (200, {"run_ts": None})


def test_health_answers_503_when_the_database_refuses_the_connection():
    def refuse():
        raise psycopg2.OperationalError("connection refused\n")

    assert _get("/health", refuse) == (503, {"error": "connection refused"})


def test_an_unknown_path_is_404():
    assert _get("/runs", lambda: FakeConnection(None)) == (404, {"error": "not found"})
