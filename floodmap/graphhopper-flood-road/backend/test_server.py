"""End-to-end regression pass for server.py's HTTP surface, against a real PostGIS and a stub
GraphHopper. Covers artifacts/TODOS.md's "Backend hardening/validation for the GraphHopper
flood-road backend" item: a real HTTP client makes a real request against the real Handler
class, and a stub GraphHopper server records exactly what body it received, so this catches a
regression in the flood-grading-to-routing wiring, not just in derive_areas() in isolation
(see test_flood_areas.py for that).

Run it against a throwaway PostGIS (needs the postgis extension, not plain Postgres):

    docker run -d --rm --name flood-verify-pg -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=floodtest -p 55432:5432 postgis/postgis:15-3.4
    PYTHONPATH=../scripts \
        FLOOD_TEST_DSN='postgresql://postgres:test@127.0.0.1:55432/floodtest' \
        python test_server.py
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib.parse import quote, urlparse

import psycopg2

VALID_TIME = "2026-05-22T09:00:00+00:00"
RUN = "2026-05-22T06:00:00+00:00"
# Depth 0.25m clears motorbike's b4 band (>= 0.20m), so a route request with this
# valid_time must come out graded: flood_areas.derive_areas returns a non-empty
# FeatureCollection, and server._handle_route must inject ch.disable + custom_model.
FLOODED_SEGMENT = "LINESTRING(105.7610 21.0214, 105.7615 21.0216)"

GRAPHHOPPER_RESPONSE = {"paths": [{"distance": 123.4, "time": 4560, "points": "stub"}]}


def reset(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cur.execute("DROP TABLE IF EXISTS flood_road_values;")
        cur.execute(
            """
            CREATE TABLE flood_road_values (
                timestamp timestamptz NOT NULL,
                forecast_time timestamptz NOT NULL,
                depth double precision NOT NULL,
                geom_4326 geometry(Geometry, 4326) NOT NULL
            );
            """
        )
        cur.execute(
            "INSERT INTO flood_road_values VALUES (%s, %s, 0.25, ST_GeomFromText(%s, 4326));",
            (RUN, VALID_TIME, FLOODED_SEGMENT),
        )
    conn.commit()


class StubGraphHopper(BaseHTTPRequestHandler):
    """Records every /route body it receives so tests can assert on it directly,
    instead of trusting server.py's own claim about what it forwarded."""

    received_bodies: list[dict] = []

    def log_message(self, *args) -> None:  # quiet the default stderr access log
        pass

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/health":
            self._send(200, {})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if urlparse(self.path).path == "/route":
            type(self).received_bodies.append(body)
            self._send(200, GRAPHHOPPER_RESPONSE)
        else:
            self._send(404, {"error": "not found"})

    def _send(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def request(url: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main() -> int:
    dsn = os.environ.get("FLOOD_TEST_DSN")
    if not dsn:
        print("FLOOD_TEST_DSN unset; skipping", file=sys.stderr)
        return 0

    parsed = urlparse(dsn)
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE 'UTC';")
    reset(conn)
    conn.close()

    import db  # noqa: E402  (backend dir is on sys.path when run from there)

    db.DB_CONFIG.update(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )

    stub = HTTPServer(("127.0.0.1", 0), StubGraphHopper)
    threading.Thread(target=stub.serve_forever, daemon=True).start()

    import server  # noqa: E402  (must import after db.DB_CONFIG is patched)

    server.GRAPHHOPPER_URL = f"http://127.0.0.1:{stub.server_port}"

    backend = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=backend.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{backend.server_port}"

    try:
        status, payload = request(f"{base}/health")
        assert status == 200, (status, payload)
        assert payload["graphhopper"]["ok"] is True, payload
        assert payload["postgis"]["ok"] is True, payload

        status, payload = request(f"{base}/flood/areas")
        assert status == 400, (status, payload)
        assert "valid_time" in payload["error"], payload

        status, payload = request(
            f"{base}/flood/areas?valid_time={quote(VALID_TIME)}&run={quote(RUN)}"
        )
        assert status == 200, (status, payload)
        assert [f["properties"]["band"] for f in payload["features"]] == ["b4"], payload

        # A route request carrying valid_time over flooded geometry must reach GraphHopper
        # graded: ch.disable and custom_model present, and flood-only fields stripped.
        StubGraphHopper.received_bodies.clear()
        status, payload = request(
            f"{base}/route",
            method="POST",
            body={
                "points": [[105.7610, 21.0214], [105.7625, 21.0220]],
                "profile": "motorbike",
                "valid_time": VALID_TIME,
                "run": RUN,
            },
        )
        assert status == 200, (status, payload)
        assert payload == GRAPHHOPPER_RESPONSE, payload
        assert len(StubGraphHopper.received_bodies) == 1
        graded_body = StubGraphHopper.received_bodies[0]
        assert graded_body["ch.disable"] is True, graded_body
        assert "custom_model" in graded_body, graded_body
        assert "valid_time" not in graded_body, graded_body

        # No valid_time: no flood grading, request forwarded as-is.
        StubGraphHopper.received_bodies.clear()
        status, payload = request(
            f"{base}/route",
            method="POST",
            body={"points": [[105.7610, 21.0214], [105.7625, 21.0220]], "profile": "motorbike"},
        )
        assert status == 200, (status, payload)
        assert payload == GRAPHHOPPER_RESPONSE, payload
        plain_body = StubGraphHopper.received_bodies[0]
        assert "ch.disable" not in plain_body, plain_body
        assert "custom_model" not in plain_body, plain_body
    finally:
        backend.shutdown()
        stub.shutdown()

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
