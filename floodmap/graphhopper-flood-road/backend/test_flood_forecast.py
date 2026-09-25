"""Regression pass for POST /flood/forecast (flood_forecast.py), through server.py's real Handler
against a real PostGIS.

The body parsing and route sampling checks need no database and always run. The endpoint checks
need a throwaway PostGIS with postgis_raster:

    docker run -d --rm --name flood-verify-pg -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=floodtest -p 55432:5432 postgis/postgis:15-3.4
    PYTHONPATH=../../../scripts/database \
        FLOOD_TEST_DSN='postgresql://postgres:test@127.0.0.1:55432/floodtest' \
        python test_flood_forecast.py

Tiles are built in SQL, one uniform value per tile, so every expected figure is a literal. Each
(run, valid_time) raster is two 2x2-pixel tiles of 0.01 degrees side by side: LEFT spans lon
105.80 to 105.82, RIGHT spans 105.82 to 105.84, both lat 21.00 to 21.02.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

import flood_forecast

# Symmetric about the tile edge at lon 105.82, and 80 samples long, so exactly 40 samples fall in
# each tile and none on the edge.
ROUTE = [[105.8105, 21.005], [105.8295, 21.005]]
ON_TILE_EDGE = [[105.82, 21.005]]
OUTSIDE_RASTER = [[100.0, 10.0]]

OLD_RUN, NEW_RUN = "20260522T084500", "20260522T090000"
# (run, valid_time_utc, left tile depth, right tile depth). Every value is exact in float32.
RASTERS = [
    (OLD_RUN, "2026-05-22 09:00", 0.5, 0.0),
    (OLD_RUN, "2026-05-22 09:15", 0.25, 0.25),
    (OLD_RUN, "2026-05-22 09:30", 1.0, 1.0),
    (NEW_RUN, "2026-05-22 09:15", 0.5, 0.25),
    # Dry in the newer run: the older run's 1.0 must not leak through.
    (NEW_RUN, "2026-05-22 09:30", 0.0, 0.0),
    (NEW_RUN, "2026-05-22 09:45", 0.75, 0.25),
    # No raster at 10:00 in any run.
    (NEW_RUN, "2026-05-22 10:15", 0.125, 0.125),
    # The window [09:00, 10:30) excludes its end.
    (NEW_RUN, "2026-05-22 10:30", 2.0, 2.0),
]
WINDOW = {"from": "2026-05-22T16:00:00+07:00", "steps": 6}

_INSERT_TILE_SQL = """
INSERT INTO flood_depth_raster_tile (run_ts, valid_time_utc, tile_x, tile_y, rast)
VALUES (%(run)s, %(valid_time)s, %(tile_x)s, 0,
        ST_AddBand(ST_MakeEmptyRaster(2, 2, %(ulx)s, 21.02, 0.01, -0.01, 0, 0, 4326), '32BF', %(depth)s, 0));
"""


def check_parsing() -> None:
    now = datetime(2026, 5, 22, 9, 22, 41, 5, tzinfo=timezone.utc)
    query = flood_forecast.parse_forecast_body({"points": ROUTE}, now)
    assert query.start_utc == datetime(2026, 5, 22, 9, 15), query
    assert query.steps == 8, query
    assert query.points == ((105.8105, 21.005), (105.8295, 21.005)), query

    query = flood_forecast.parse_forecast_body({"points": ROUTE, **WINDOW}, now)
    assert (query.start_utc, query.steps) == (datetime(2026, 5, 22, 9, 0), 6), query

    bad_bodies = [
        ([], "JSON object"),
        ({}, "points is required"),
        ({"points": []}, "points is required"),
        ({"points": [[105.8, 21.0]] * 2001}, "at most 2000"),
        ({"points": [[105.8]]}, "points[0] must be [lon, lat]"),
        ({"points": [[105.8, 21.0], ["a", 21.0]]}, "points[1] must be [lon, lat]"),
        ({"points": [[181.0, 21.0]]}, "points[0] is out of range"),
        ({"points": ROUTE, "from": "yesterday"}, "not ISO 8601"),
        ({"points": ROUTE, "from": "2026-05-22T16:00:00"}, "UTC offset"),
        ({"points": ROUTE, "steps": 0}, "steps must be"),
        ({"points": ROUTE, "steps": "8"}, "steps must be"),
    ]
    for body, message in bad_bodies:
        try:
            flood_forecast.parse_forecast_body(body, now)
        except ValueError as exc:
            assert message in str(exc), (body, str(exc))
        else:
            raise AssertionError(f"accepted {body!r}")


def check_sampling() -> None:
    samples = flood_forecast.sample_polyline(((0.0, 0.0), (0.0, 0.001)))
    assert [round(lat, 10) for _, lat in samples] == [0.0, 0.0002, 0.0004, 0.0006, 0.0008, 0.001], samples

    # An extra vertex mid-segment does not change where the samples fall.
    straight = flood_forecast.sample_polyline(tuple(map(tuple, ROUTE)))
    with_vertex = flood_forecast.sample_polyline(((105.8105, 21.005), (105.815, 21.005), (105.8295, 21.005)))
    assert len(straight) == 80 and len(with_vertex) == 80, (len(straight), len(with_vertex))
    assert all(abs(a[0] - b[0]) < 1e-9 for a, b in zip(straight, with_vertex))
    assert sum(1 for lon, _ in straight if lon < 105.82) == 40

    assert len(flood_forecast.sample_polyline(((105.0, 21.0), (106.0, 21.0)))) == 200
    assert flood_forecast.sample_polyline(((105.8, 21.0), (105.8, 21.0))) == [(105.8, 21.0)]


def load_rasters(conn) -> None:
    import create_flood_depth_raster_tables

    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS flood_depth_raster_tile;")
        cur.execute(create_flood_depth_raster_tables.SQL)
        for run, valid_time, left, right in RASTERS:
            for tile_x, ulx, depth in ((0, 105.80, left), (1, 105.82, right)):
                cur.execute(
                    _INSERT_TILE_SQL,
                    {"run": run, "valid_time": valid_time, "tile_x": tile_x, "ulx": ulx, "depth": depth},
                )
    conn.commit()


def post(url: str, body: object) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def column(valid_time: str, run: str, mean, deepest, wet_fraction) -> dict:
    return {
        "valid_time": valid_time,
        "run": run,
        "mean_depth_m": mean,
        "max_depth_m": deepest,
        "wet_fraction": wet_fraction,
    }


def check_endpoint(dsn: str) -> None:
    import psycopg2

    conn = psycopg2.connect(dsn)
    load_rasters(conn)
    conn.close()

    import db  # noqa: E402  (backend dir is on sys.path when run from there)

    parsed = urlparse(dsn)
    db.DB_CONFIG.update(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )

    import server  # noqa: E402  (must import after db.DB_CONFIG is patched)

    backend = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=backend.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{backend.server_port}/flood/forecast"
    try:
        status, payload = post(url, {"points": ROUTE, **WINDOW})
        assert status == 200, (status, payload)
        assert payload == {
            "columns": [
                column("2026-05-22T16:00:00+07:00", OLD_RUN, 0.25, 0.5, 0.5),
                column("2026-05-22T16:15:00+07:00", NEW_RUN, 0.375, 0.5, 1.0),
                column("2026-05-22T16:30:00+07:00", NEW_RUN, 0.0, 0.0, 0.0),
                column("2026-05-22T16:45:00+07:00", NEW_RUN, 0.5, 0.75, 1.0),
                column("2026-05-22T17:15:00+07:00", NEW_RUN, 0.125, 0.125, 1.0),
            ]
        }, payload

        # The edge pixel belongs to RIGHT; LEFT's hull touches the point but has no pixel there.
        status, payload = post(url, {"points": ON_TILE_EDGE, "from": "2026-05-22T16:45:00+07:00", "steps": 1})
        assert status == 200, (status, payload)
        assert payload == {"columns": [column("2026-05-22T16:45:00+07:00", NEW_RUN, 0.25, 0.25, 1.0)]}, payload

        status, payload = post(url, {"points": OUTSIDE_RASTER, "from": "2026-05-22T16:45:00+07:00", "steps": 1})
        assert status == 200, (status, payload)
        assert payload == {"columns": [column("2026-05-22T16:45:00+07:00", NEW_RUN, None, None, None)]}, payload

        status, payload = post(url, {"points": ROUTE, "from": "2026-05-23T16:00:00+07:00"})
        assert (status, payload) == (200, {"columns": []}), (status, payload)

        status, payload = post(url, {"points": []})
        assert status == 400 and "points is required" in payload["error"], (status, payload)

        req = urllib.request.Request(url, data=b"{not json", method="POST")
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as exc:
            assert exc.code == 400, exc.code
        else:
            raise AssertionError("accepted a body that is not JSON")
    finally:
        backend.shutdown()


def main() -> int:
    check_parsing()
    check_sampling()
    dsn = os.environ.get("FLOOD_TEST_DSN")
    if not dsn:
        print("FLOOD_TEST_DSN unset; skipping the endpoint checks", file=sys.stderr)
    else:
        check_endpoint(dsn)
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
