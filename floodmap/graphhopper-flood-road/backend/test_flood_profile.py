"""Regression pass for POST /flood/profile (flood_profile.py), through server.py's real Handler
against a real PostGIS.

The body parsing checks need no database and always run. The endpoint checks need a throwaway
PostGIS with postgis_raster, set up as in test_flood_forecast.py:

    docker run -d --rm --name flood-verify-pg -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=floodtest -p 55432:5432 postgis/postgis:15-3.4
    PYTHONPATH=../../../scripts/database \
        FLOOD_TEST_DSN='postgresql://postgres:test@127.0.0.1:55432/floodtest' \
        python test_flood_profile.py

The fixtures are test_flood_forecast's: two 2x2-pixel tiles side by side, one uniform value each,
so every expected depth is a literal.
"""

from __future__ import annotations

import os
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

import flood_profile
from test_flood_forecast import NEW_RUN, ON_TILE_EDGE, OUTSIDE_RASTER, ROUTE, load_rasters, post

WET_STEP = "2026-05-22T16:15:00+07:00"
DRY_STEP = "2026-05-22T16:30:00+07:00"


def check_parsing() -> None:
    query = flood_profile.parse_profile_body({"points": ROUTE, "valid_time": WET_STEP, "run": NEW_RUN})
    assert query.points == ((105.8105, 21.005), (105.8295, 21.005)), query
    assert query.valid_utc == datetime(2026, 5, 22, 9, 15), query
    assert query.run == NEW_RUN, query

    bad_bodies = [
        ([], "JSON object"),
        ({}, "points is required"),
        ({"points": []}, "points is required"),
        ({"points": [[105.8]], "valid_time": WET_STEP, "run": NEW_RUN}, "points[0] must be [lon, lat]"),
        ({"points": ROUTE, "run": NEW_RUN}, "valid_time is required"),
        ({"points": ROUTE, "valid_time": "yesterday", "run": NEW_RUN}, "not ISO 8601"),
        ({"points": ROUTE, "valid_time": "2026-05-22T16:15:00", "run": NEW_RUN}, "UTC offset"),
        ({"points": ROUTE, "valid_time": WET_STEP}, "run is required"),
        ({"points": ROUTE, "valid_time": WET_STEP, "run": ""}, "run is required"),
    ]
    for body, message in bad_bodies:
        try:
            flood_profile.parse_profile_body(body)
        except ValueError as exc:
            assert message in str(exc), (body, str(exc))
        else:
            raise AssertionError(f"accepted {body!r}")


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
    url = f"http://127.0.0.1:{backend.server_port}/flood/profile"
    try:
        # 80 samples, 40 in each tile. NEW_RUN's 09:15 raster is 0.5 m left and 0.25 m right.
        status, payload = post(url, {"points": ROUTE, "valid_time": WET_STEP, "run": NEW_RUN})
        assert status == 200, (status, payload)
        samples = payload["samples"]
        assert len(samples) == 80, len(samples)
        assert [s["depth_m"] for s in samples] == [0.5] * 40 + [0.25] * 40, [s["depth_m"] for s in samples]
        assert (samples[0]["lon"], samples[0]["lat"]) == (105.8105, 21.005), samples[0]
        assert abs(samples[-1]["lon"] - 105.8295) < 1e-9, samples[-1]
        assert all(a["lon"] < b["lon"] for a, b in zip(samples, samples[1:])), "samples out of route order"

        # A dry raster gives 0.0, never null, so dry reads as "inside the raster, no water".
        status, payload = post(url, {"points": ROUTE, "valid_time": DRY_STEP, "run": NEW_RUN})
        assert status == 200, (status, payload)
        assert {s["depth_m"] for s in payload["samples"]} == {0.0}, payload["samples"][:3]

        # The edge pixel belongs to RIGHT (0.25 m).
        status, payload = post(url, {"points": ON_TILE_EDGE, "valid_time": WET_STEP, "run": NEW_RUN})
        assert status == 200 and [s["depth_m"] for s in payload["samples"]] == [0.25], (status, payload)

        # Outside the raster: null, so it never reads as dry.
        status, payload = post(url, {"points": OUTSIDE_RASTER, "valid_time": WET_STEP, "run": NEW_RUN})
        assert status == 200 and [s["depth_m"] for s in payload["samples"]] == [None], (status, payload)

        # No raster for that run and time: 404, not a list of nulls.
        status, payload = post(url, {"points": ROUTE, "valid_time": "2026-05-23T16:15:00+07:00", "run": NEW_RUN})
        assert status == 404 and "no depth raster" in payload["error"], (status, payload)

        status, payload = post(url, {"points": ROUTE, "run": NEW_RUN})
        assert status == 400 and "valid_time is required" in payload["error"], (status, payload)

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
    dsn = os.environ.get("FLOOD_TEST_DSN")
    if not dsn:
        print("FLOOD_TEST_DSN unset; skipping the endpoint checks", file=sys.stderr)
    else:
        check_endpoint(dsn)
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
