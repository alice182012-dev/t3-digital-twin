"""End-to-end regression pass for server.py's HTTP surface, against a real PostGIS and a stub
GraphHopper. Covers artifacts/TODOS.md's "Backend hardening/validation for the GraphHopper
flood-road backend" item: a real HTTP client makes a real request against the real Handler
class, and a stub GraphHopper server records exactly what body it received, so this catches a
regression in the flood-grading-to-routing wiring, not just in derive_areas() in isolation
(see test_flood_areas.py for that).

Run it against a throwaway PostGIS with postgis_raster, and a Python with GDAL (osgeo) and
gdallocationinfo on PATH:

    docker run -d --rm --name flood-verify-pg -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=floodtest -p 55432:5432 postgis/postgis:15-3.4
    PYTHONPATH=../scripts:../../../scripts/flood_extent:../../../scripts/database \
        FLOOD_TEST_DSN='postgresql://postgres:test@127.0.0.1:55432/floodtest' \
        python test_server.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlencode, urlparse

import numpy as np
import psycopg2
from osgeo import gdal, osr

import create_flood_depth_raster_tables
import create_flood_extent_tables
import create_flood_road_tables
import raster_load

gdal.UseExceptions()

VALID_TIME = "2026-05-22T09:00:00+00:00"
RUN = "2026-05-22T06:00:00+00:00"
# Depth 0.25m clears motorbike's b4 band (>= 0.20m), so a route request with this
# valid_time must come out graded: flood_areas.derive_areas returns a non-empty
# FeatureCollection, and server._handle_route must inject ch.disable + custom_model.
FLOODED_SEGMENT = "LINESTRING(105.7610 21.0214, 105.7615 21.0216)"

GRAPHHOPPER_RESPONSE = {"paths": [{"distance": 123.4, "time": 4560, "points": "stub"}]}

OLD_RUN = "20260522T060000"
NEW_RUN = "20260522T120000"
# depth_*.tif filenames are Vietnam local time. 16:00 local exists in both runs; 19:00 local only
# in OLD_RUN, so "latest" must 404 on it instead of falling back to the older run.
SHARED_FILE, SHARED_VALID_TIME = "depth_20260522_160000.tif", "2026-05-22T16:00:00+07:00"
OLD_ONLY_FILE, OLD_ONLY_VALID_TIME = "depth_20260522_190000.tif", "2026-05-22T19:00:00+07:00"

# A 600x600 grid of 10 m pixels in EPSG:3405 near Hanoi, the source SRID of real depth.tif files.
# 600 pixels span three raster_load.TILE_SIZE tiles each way, so lookups cross tile edges.
ORIGIN_X, ORIGIN_Y, PIXEL_M, SIZE = 583000.0, 2327000.0, 10.0, 600
WET_PIXEL, DRY_PIXEL = (12, 12), (2, 2)


def depth_grid(offset: float) -> np.ndarray:
    """Distinct value per pixel, so a lookup that lands one pixel off fails the equality check.
    The top-left 5x5 block is 0, which calculate_depth.py also declares as NoData."""
    grid = (np.arange(SIZE * SIZE, dtype=np.float32).reshape(SIZE, SIZE) + 1) * 0.01 + offset
    grid[:5, :5] = 0
    return grid


def write_depth_tif(path: Path, grid: np.ndarray) -> None:
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3405)
    ds = gdal.GetDriverByName("GTiff").Create(str(path), SIZE, SIZE, 1, gdal.GDT_Float32)
    ds.SetGeoTransform([ORIGIN_X, PIXEL_M, 0.0, ORIGIN_Y, 0.0, -PIXEL_M])
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.WriteArray(grid)
    band.SetNoDataValue(0)
    ds.FlushCache()
    ds = None


def pixel_centre_lonlat(row: int, col: int) -> tuple[float, float]:
    src, dst = osr.SpatialReference(), osr.SpatialReference()
    src.ImportFromEPSG(3405)
    dst.ImportFromEPSG(4326)
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    x = ORIGIN_X + (col + 0.5) * PIXEL_M
    y = ORIGIN_Y - (row + 0.5) * PIXEL_M
    lon, lat, _ = osr.CoordinateTransformation(src, dst).TransformPoint(x, y)
    return lon, lat


def gdallocationinfo_value(tif: Path, lon: float, lat: float) -> float:
    out = subprocess.run(
        ["gdallocationinfo", "-valonly", "-wgs84", str(tif), repr(lon), repr(lat)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def pixels_around_boundary(tif_4326: Path, lon: float, lat: float) -> list[np.float32]:
    """The four pixels that touch the pixel boundary nearest the point. A tile-edge point sits a
    float-noise hair off the boundary, so either neighbor is a correct answer there, and the test
    accepts these four pixels and nothing else."""
    ds = gdal.Open(str(tif_4326))
    ulx, scale_x, _, uly, _, scale_y = ds.GetGeoTransform()
    col, row = round((lon - ulx) / scale_x), round((lat - uly) / scale_y)
    window = ds.GetRasterBand(1).ReadAsArray(col - 1, row - 1, 2, 2)
    return [np.float32(value) for value in window.ravel()]


def tile_edge_lonlat(tif_4326: Path, tile_x: float, tile_y: float) -> tuple[float, float]:
    """The EPSG:4326 point tile_x and tile_y tiles in from the raster's top-left corner; a whole
    number lands on a tile edge, so this names points that several tiles' hulls share."""
    ds = gdal.Open(str(tif_4326))
    ulx, scale_x, _, uly, _, scale_y = ds.GetGeoTransform()
    return ulx + tile_x * raster_load.TILE_SIZE * scale_x, uly + tile_y * raster_load.TILE_SIZE * scale_y


def load_depth_runs(conn, workdir: Path) -> Path:
    """Loads OLD_RUN and NEW_RUN through raster_load.load_run, the same path the DAG uses.
    Returns NEW_RUN's source depth.tif for the gdallocationinfo acceptance check."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS flood_depth_raster_tile, flood_extent_polygon;")
        cur.execute(create_flood_depth_raster_tables.SQL)
        cur.execute(create_flood_extent_tables.SQL)
    conn.commit()

    runs = {OLD_RUN: ([SHARED_FILE, OLD_ONLY_FILE], 0.0), NEW_RUN: ([SHARED_FILE], 10.0)}
    for run, (files, offset) in runs.items():
        depth_dir = workdir / run
        depth_dir.mkdir()
        for name in files:
            write_depth_tif(depth_dir / name, depth_grid(offset))
        for valid_time in raster_load.load_run(conn, depth_dir, run, workdir / "warp"):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO flood_extent_polygon (run_ts, valid_time_utc, dn_code, area_m2, geom)"
                    " VALUES (%s, %s, 1, 100, ST_GeomFromText('POINT(105.8 21.0)', 4326));",
                    (run, valid_time),
                )
    conn.commit()
    return workdir / NEW_RUN / SHARED_FILE


def points_url(base: str, **params) -> str:
    return f"{base}/flood/points?{urlencode(params)}"


def reset(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS flood_road_values, flood_road_file;")
        cur.execute(create_flood_road_tables.SQL)
        cur.execute("INSERT INTO flood_road_file (id, timestamp, source_file) VALUES (1, %s, 'test');", (RUN,))
        cur.execute(
            "INSERT INTO flood_road_values (file_id, timestamp, forecast_time, depth, geom_4326)"
            " VALUES (1, %s, %s, 0.25, ST_GeomFromText(%s, 4326));",
            (RUN, VALID_TIME, FLOODED_SEGMENT),
        )
    conn.commit()


class StubGraphHopper(BaseHTTPRequestHandler):
    """Records every /route body it receives so tests can assert on it directly,
    instead of trusting server.py's own claim about what it forwarded."""

    received_bodies: list[dict] = []
    response_override: dict | None = None  # when set, /route answers with this instead of GRAPHHOPPER_RESPONSE

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
            self._send(200, type(self).response_override or GRAPHHOPPER_RESPONSE)
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
    workdir = TemporaryDirectory()
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        # raster_load writes a tz-aware UTC datetime into a TIMESTAMP column, so the stored value
        # is UTC only when the session is, as on storage-postgres.
        cur.execute("SET TIME ZONE 'UTC';")
    reset(conn)
    source_tif = load_depth_runs(conn, Path(workdir.name))
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

        # TIME_AWARE_ROUTING on (US-052), against a GraphHopper that does not run the engine: the first request carries
        # td_departure and no flood grading, the answer has no td.status, so the backend sends today's graded request and
        # marks the response as a fallback.
        os.environ["TIME_AWARE_ROUTING"] = "true"
        try:
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
        finally:
            del os.environ["TIME_AWARE_ROUTING"]
        assert status == 200, (status, payload)
        assert len(StubGraphHopper.received_bodies) == 2, StubGraphHopper.received_bodies
        engine_body, fallback_body = StubGraphHopper.received_bodies
        assert isinstance(engine_body["td_departure"], int), engine_body
        assert "custom_model" not in engine_body and "ch.disable" not in engine_body, engine_body
        assert "td_departure" not in fallback_body, fallback_body
        assert fallback_body["ch.disable"] is True and "custom_model" in fallback_body, fallback_body
        assert payload["paths"] == GRAPHHOPPER_RESPONSE["paths"], payload
        assert payload["hints"]["td.status"] == "fallback", payload

        # POST /route/departures (US-053): the usual route with its edge_id and time details, the depth table from the
        # EDGE_TABLE_DIR volume, and the sticky rule. Edge 1 is wet at the first three steps, and now lies in the second step.
        import struct
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        first_step = now.replace(minute=now.minute - now.minute % 15, second=0, microsecond=0) - timedelta(minutes=15)
        graph_hash, run = "c" * 64, "20261005T170000"
        packed = bytearray(struct.pack("<4sHHIHH", b"EDGD", 1, 8, 2, len(graph_hash), len(run)) + graph_hash.encode() + run.encode())
        for i in range(8):
            packed += struct.pack("<q", int((first_step + timedelta(minutes=15 * i)).timestamp()))
        for edge in range(2):
            for step in range(8):
                packed += struct.pack("<H", 50 if edge == 1 and step <= 2 else 0)
        with TemporaryDirectory() as tables:
            Path(tables, "20261005T170000.bin").write_bytes(bytes(packed))
            Path(tables, "latest").write_text("20261005T170000.bin\n", encoding="utf-8")
            os.environ["EDGE_TABLE_DIR"] = tables
            StubGraphHopper.response_override = {
                "paths": [{"distance": 600.0, "time": 120000, "details": {
                    "edge_id": [[0, 1, 0], [1, 2, 1]], "time": [[0, 1, 60000], [1, 2, 60000]]}}],
                "hints": {"td.graph_hash": graph_hash, "td.run": run},
            }
            try:
                StubGraphHopper.received_bodies.clear()
                status, payload = request(
                    f"{base}/route/departures",
                    method="POST",
                    body={"points": [[105.7610, 21.0214], [105.7625, 21.0220]], "profile": "car", "now": "2030-01-01T00:00:00Z", "margin_s": 0},
                )
                assert status == 200, (status, payload)
                assert payload["status"] == "ok", payload
                assert payload["run"] == run and payload["margin_s"] == 600 and payload["limit_cm"] == 30, payload
                assert abs(payload["run_age_s"] - (now - first_step).total_seconds()) < 5, payload
                assert [c["status"] for c in payload["candidates"][:3]] == ["blocked", "blocked", "clear"], payload["candidates"]
                assert payload["earliest_clear"]["departure"] == (first_step + timedelta(minutes=45)).isoformat(), payload
                sent = StubGraphHopper.received_bodies[0]
                assert sent["details"] == ["edge_id", "time"] and sent["td_info"] is True, sent
                assert "custom_model" not in sent and "td_departure" not in sent, sent

                # The table was built for another graph: unavailable, not an error, and both hashes are named.
                StubGraphHopper.response_override["hints"]["td.graph_hash"] = "d" * 64
                status, payload = request(
                    f"{base}/route/departures", method="POST",
                    body={"points": [[105.7610, 21.0214], [105.7625, 21.0220]], "profile": "car"},
                )
                assert status == 200 and payload["status"] == "unavailable", (status, payload)
                assert "c" * 64 in payload["reason"] and "d" * 64 in payload["reason"], payload

                # No pointer in the folder.
                Path(tables, "latest").unlink()
                status, payload = request(
                    f"{base}/route/departures", method="POST",
                    body={"points": [[105.7610, 21.0214], [105.7625, 21.0220]], "profile": "car"},
                )
                assert status == 200 and payload["status"] == "unavailable", (status, payload)

                status, payload = request(f"{base}/route/departures", method="POST", body={"profile": "car"})
                assert status == 400, (status, payload)
            finally:
                StubGraphHopper.response_override = None
                del os.environ["EDGE_TABLE_DIR"]

        wet_lon, wet_lat = pixel_centre_lonlat(*WET_PIXEL)
        expected_depth = gdallocationinfo_value(source_tif, wet_lon, wet_lat)
        status, payload = request(points_url(base, lat=wet_lat, lon=wet_lon, valid_time=SHARED_VALID_TIME))
        assert status == 200, (status, payload)
        # gdallocationinfo prints 15 significant digits, the endpoint the full double of the same
        # float32 pixel, so compare at the raster's own precision.
        assert np.float32(payload.pop("depth_m")) == np.float32(expected_depth), (payload, expected_depth)
        assert payload == {
            "lat": wet_lat,
            "lon": wet_lon,
            "valid_time": SHARED_VALID_TIME,
            "run": NEW_RUN,
            "status": "wet",
        }, payload

        status, payload = request(
            points_url(base, lat=wet_lat, lon=wet_lon, valid_time=SHARED_VALID_TIME, run=OLD_RUN)
        )
        assert status == 200, (status, payload)
        assert payload["run"] == OLD_RUN, payload
        assert np.float32(payload["depth_m"]) == depth_grid(0.0)[WET_PIXEL], payload

        dry_lon, dry_lat = pixel_centre_lonlat(*DRY_PIXEL)
        status, payload = request(points_url(base, lat=dry_lat, lon=dry_lon, valid_time=SHARED_VALID_TIME))
        assert status == 200, (status, payload)
        assert (payload["status"], payload["depth_m"]) == ("dry", 0.0), payload

        # The loaded tiles are cut from this reprojected grid, so it is the reference for points
        # on a tile edge, where the source tif's own pixel grid doesn't line up.
        warped_tif = Path(workdir.name) / "new_run_4326.tif"
        raster_load.reproject_to_4326(source_tif, warped_tif)
        edge_points = {
            "corner of four tiles": tile_edge_lonlat(warped_tif, 1, 1),
            "edge of two tiles": tile_edge_lonlat(warped_tif, 2, 0.5),
        }
        for name, (edge_lon, edge_lat) in edge_points.items():
            neighbours = pixels_around_boundary(warped_tif, edge_lon, edge_lat)
            assert len(set(neighbours)) == 4, (name, neighbours)
            status, payload = request(points_url(base, lat=edge_lat, lon=edge_lon, valid_time=SHARED_VALID_TIME))
            assert status == 200, (name, status, payload)
            assert payload["status"] == "wet", (name, payload)
            assert np.float32(payload["depth_m"]) in neighbours, (name, payload, neighbours)

        status, payload = request(points_url(base, lat=10.0, lon=100.0, valid_time=SHARED_VALID_TIME))
        assert status == 200, (status, payload)
        assert (payload["status"], payload["depth_m"]) == ("no_data", None), payload

        status, payload = request(points_url(base, lat=wet_lat, lon=wet_lon, valid_time=OLD_ONLY_VALID_TIME))
        assert status == 404, (status, payload)
        assert NEW_RUN in payload["error"], payload

        status, payload = request(points_url(base, lat=10.0, lon=100.0, valid_time="2026-05-23T01:00:00+07:00"))
        assert status == 404, (status, payload)
        assert "2026-05-23T01:00:00+07:00" in payload["error"], payload

        status, payload = request(
            points_url(base, lat=wet_lat, lon=wet_lon, valid_time=SHARED_VALID_TIME, run="20260101T000000")
        )
        assert status == 404, (status, payload)

        bad_requests = [
            ({"lon": wet_lon, "valid_time": SHARED_VALID_TIME}, "lat is required"),
            ({"lat": "abc", "lon": wet_lon, "valid_time": SHARED_VALID_TIME}, "lat is not a number"),
            ({"lat": 95, "lon": wet_lon, "valid_time": SHARED_VALID_TIME}, "lat must be between"),
            ({"lat": wet_lat, "lon": "nan", "valid_time": SHARED_VALID_TIME}, "lon must be between"),
            ({"lat": wet_lat, "lon": wet_lon}, "valid_time is required"),
            ({"lat": wet_lat, "lon": wet_lon, "valid_time": "yesterday"}, "not ISO 8601"),
            ({"lat": wet_lat, "lon": wet_lon, "valid_time": "2026-05-22T16:00:00"}, "UTC offset"),
        ]
        for params, message in bad_requests:
            status, payload = request(points_url(base, **params))
            assert status == 400 and message in payload["error"], (params, status, payload)
    finally:
        backend.shutdown()
        stub.shutdown()
        workdir.cleanup()

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
