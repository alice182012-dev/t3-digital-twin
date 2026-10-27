#!/usr/bin/env python3
"""The analysis service (US-109).

GET /health returns the newest run_ts that has every core output in flood_run_output, the run manifest of US-108,
or null when no run has all of them. The service reads storage-postgres as analysis_reader (US-107).
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import psycopg2

# The values of run_output.Output in scripts/database/run_output.py. The image does not ship scripts/, so the names
# are repeated here, and test/test_server.py fails when the two differ.
CORE_OUTPUTS = frozenset({"depth_raster", "extent", "edge_depth"})

READER_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "storage-postgres"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "database": os.environ.get("POSTGRES_DB", "minio_custom"),
    "user": os.environ.get("ANALYSIS_READER_USER", "analysis_reader"),
    "password": os.environ.get("ANALYSIS_READER_PASSWORD"),
}

# run_ts is a fixed-width YYYYMMDDTHHMMSS string, so its text order is its time order.
_NEWEST_COMPLETE_RUN_SQL = """
SELECT run_ts FROM flood_run_output
GROUP BY run_ts
HAVING array_agg(DISTINCT output ORDER BY output) = %(outputs)s::text[]
ORDER BY run_ts DESC
LIMIT 1
"""


def newest_complete_run(conn) -> str | None:
    """The newest run_ts whose outputs in flood_run_output are exactly CORE_OUTPUTS, or None."""
    with conn.cursor() as cur:
        cur.execute(_NEWEST_COMPLETE_RUN_SQL, {"outputs": sorted(CORE_OUTPUTS)})
        row = cur.fetchone()
    return row[0] if row else None


def connect():
    return psycopg2.connect(**READER_CONFIG)


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/health":
            self._send(404, {"error": "not found"})
            return
        try:
            conn = connect()
            try:
                run_ts = newest_complete_run(conn)
            finally:
                conn.close()
        except psycopg2.Error as exc:
            self._send(503, {"error": str(exc).strip()})
            return
        self._send(200, {"run_ts": run_ts})


def main() -> int:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8020"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Analysis service listening on http://{host}:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
