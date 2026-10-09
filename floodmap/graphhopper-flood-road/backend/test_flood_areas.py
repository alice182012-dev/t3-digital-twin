"""Regression pass for derive_areas() and build_custom_model(), against a real PostGIS.

Covers the routing and flood-grading behavior artifacts/TODOS.md's "Backend hardening/
validation for the GraphHopper flood-road backend" item asks for: derive_areas() is the one
place both GET /flood/areas (the map overlay) and POST /route (the routing gate) read flood
geometry from, so a regression here would silently break both at once.

Run it from the repository root against a throwaway PostGIS (needs the postgis extension,
not plain Postgres):

    docker run -d --rm --name flood-verify-pg -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=floodtest -p 55432:5432 postgis/postgis:15-3.4
    FLOOD_TEST_DSN='postgresql://postgres:test@127.0.0.1:55432/floodtest' \
        python3 floodmap/graphhopper-flood-road/backend/test_flood_areas.py

Without FLOOD_TEST_DSN it prints "FLOOD_TEST_DSN unset; skipping" and exits 0. CI treats
that line as a failure (.github/workflows/flood-areas-test.yml).

flood_areas imports flood_utils, which the Dockerfile supplies by copying ../scripts
alongside ../backend; the sys.path inserts below stand in for that outside the image. The table
comes from scripts/database/create_flood_road_tables.py, the same DDL the server runs, so a
column the query needs but the deploy step lacks fails here first.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2

_HERE = Path(__file__).resolve().parent
sys.path[:0] = [
    str(_HERE),
    str(_HERE.parent / "scripts"),
    str(_HERE.parents[2] / "scripts" / "database"),
]

import create_flood_road_tables
from flood_areas import build_custom_model, derive_areas
from flood_utils import vehicle_threshold_cm, vehicle_types

VALID_TIME = "2026-05-22T09:00:00+00:00"
RUN_OLD = "2026-05-22T06:00:00+00:00"
RUN_NEW = "2026-05-22T12:00:00+00:00"

# Motorbike threshold is 20cm (flood_utils.VEHICLE_PROFILES), so its bands are:
#   b2 [0.10, 0.15), b3 [0.15, 0.20), b4 [0.20, inf). Car's threshold is 30cm, so the
# same depths land in different bands, or no band at all, for car.
DEPTH_BELOW_ANY_BAND = 0.03
DEPTH_B2_MOTORBIKE = 0.12
DEPTH_B3_MOTORBIKE = 0.17
DEPTH_B4_MOTORBIKE = 0.25

# Two nearby but distinct short segments so ST_Union has more than one input to merge,
# without needing real road geometry. Near flood_utils.DEFAULT_ORIGIN.
SEGMENT_A = "LINESTRING(105.7610 21.0214, 105.7615 21.0216)"
SEGMENT_B = "LINESTRING(105.7620 21.0218, 105.7625 21.0220)"
# About 1 km from A, so its buffer never merges with A's and each shows up as its own feature.
SEGMENT_FAR = "LINESTRING(105.7710 21.0314, 105.7715 21.0316)"


def reset(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS flood_road_values, flood_road_file;")
        cur.execute(create_flood_road_tables.SQL)
        cur.execute("INSERT INTO flood_road_file (id, timestamp, source_file) VALUES (1, %s, 'test');", (RUN_OLD,))
    conn.commit()


def insert(conn, run: str, forecast_time: str, depth: float, wkt: str, segment_id: str | None = None) -> None:
    """segment_id=None is a row from the old GeoJSON chain; a value is a flood_on_roads.py row."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO flood_road_values (file_id, timestamp, forecast_time, depth, segment_id, geom_4326)"
            " VALUES (1, %s, %s, %s, %s, ST_GeomFromText(%s, 4326));",
            (run, forecast_time, depth, segment_id, wkt),
        )
    conn.commit()


def band_ids(areas_fc: dict) -> list[str]:
    return [feature["properties"]["band"] for feature in areas_fc["features"]]


def main() -> int:
    dsn = os.environ.get("FLOOD_TEST_DSN")
    if not dsn:
        print("FLOOD_TEST_DSN unset; skipping", file=sys.stderr)
        return 0

    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE 'UTC';")

    # Empty table: no rows for any band, not a crash.
    reset(conn)
    assert derive_areas(conn, VALID_TIME)["features"] == []

    # A depth below every band's minimum contributes no area.
    reset(conn)
    insert(conn, RUN_OLD, VALID_TIME, DEPTH_BELOW_ANY_BAND, SEGMENT_A)
    assert derive_areas(conn, VALID_TIME)["features"] == []

    # One segment in band b2 shows up as exactly one b2 feature.
    reset(conn)
    insert(conn, RUN_OLD, VALID_TIME, DEPTH_B2_MOTORBIKE, SEGMENT_A)
    fc = derive_areas(conn, VALID_TIME, "motorbike", RUN_OLD)
    assert band_ids(fc) == ["b2"], fc
    assert fc["features"][0]["properties"]["multiply_by"] == 0.2

    # Multiple bands come back deepest-first (b4, b3, b2), matching build_custom_model's
    # if/else_if ordering requirement.
    reset(conn)
    insert(conn, RUN_OLD, VALID_TIME, DEPTH_B4_MOTORBIKE, SEGMENT_A)
    insert(conn, RUN_OLD, VALID_TIME, DEPTH_B3_MOTORBIKE, SEGMENT_B)
    fc = derive_areas(conn, VALID_TIME, "motorbike", RUN_OLD)
    assert band_ids(fc) == ["b4", "b3"], fc

    # A min_area high enough that no buffered polygon clears it: every band drops out,
    # confirming the filter is live rather than a no-op.
    fc_filtered = derive_areas(conn, VALID_TIME, "motorbike", RUN_OLD, min_area_m2=1e9)
    assert fc_filtered["features"] == []

    # Same depth, different vehicle: 0.12m is band b2 for motorbike (threshold 20cm) but
    # below every band for car (threshold 30cm, b2 starts at 0.15m).
    reset(conn)
    insert(conn, RUN_OLD, VALID_TIME, DEPTH_B2_MOTORBIKE, SEGMENT_A)
    assert band_ids(derive_areas(conn, VALID_TIME, "motorbike", RUN_OLD)) == ["b2"]
    assert derive_areas(conn, VALID_TIME, "car", RUN_OLD)["features"] == []

    # run="latest" follows the newest timestamp per forecast_time; a pinned run reads only
    # that run's own rows. Same forecast_time, different depths per run, so the two answers
    # would silently agree if pinning were broken.
    reset(conn)
    insert(conn, RUN_OLD, VALID_TIME, DEPTH_B2_MOTORBIKE, SEGMENT_A)
    insert(conn, RUN_NEW, VALID_TIME, DEPTH_B4_MOTORBIKE, SEGMENT_A)
    assert band_ids(derive_areas(conn, VALID_TIME, "motorbike", "latest")) == ["b4"]
    assert band_ids(derive_areas(conn, VALID_TIME, "motorbike", RUN_OLD)) == ["b2"]
    assert band_ids(derive_areas(conn, VALID_TIME, "motorbike", RUN_NEW)) == ["b4"]

    check_depth_decides_impassable(conn)

    conn.close()

    # build_custom_model is pure: no DB needed. Deepest band first is "if", the rest
    # "else_if", so overlapping buffers from different bands never multiply together.
    areas_fc = {
        "features": [
            {"id": "b4_1", "properties": {"multiply_by": 0.0}},
            {"id": "b3_1", "properties": {"multiply_by": 0.05}},
            {"id": "b2_1", "properties": {"multiply_by": 0.2}},
        ]
    }
    model = build_custom_model(areas_fc)
    assert model["priority"] == [
        {"if": "in_b4_1", "multiply_by": "0.0"},
        {"else_if": "in_b3_1", "multiply_by": "0.05"},
        {"else_if": "in_b2_1", "multiply_by": "0.2"},
    ], model["priority"]
    assert model["areas"] is areas_fc

    print("ok")
    return 0


def check_depth_decides_impassable(conn) -> None:
    """b4 (impassable) starts at each vehicle's limit in flood_utils, and depth is the deepest
    sample along a piece (D-006). The fixtures are fractions of the limit, so a changed limit
    moves them with it."""
    for vehicle in vehicle_types():
        limit_m = vehicle_threshold_cm(vehicle) / 100.0

        reset(conn)
        insert(conn, RUN_OLD, VALID_TIME, 1.1 * limit_m, SEGMENT_A, segment_id="way/1#0")
        assert band_ids(derive_areas(conn, VALID_TIME, vehicle, RUN_OLD)) == ["b4"], (vehicle, "1.1 x limit")
        assert band_ids(derive_areas(conn, VALID_TIME, vehicle, "latest")) == ["b4"], (vehicle, "latest")

        reset(conn)
        insert(conn, RUN_OLD, VALID_TIME, 0.9 * limit_m, SEGMENT_A, segment_id="way/1#0")
        assert band_ids(derive_areas(conn, VALID_TIME, vehicle, RUN_OLD)) == ["b3"], (vehicle, "0.9 x limit")

    # A run holding old-pipeline rows (segment_id NULL) and flood_on_roads rows for one
    # forecast_time grades both on depth.
    limit_m = vehicle_threshold_cm("motorbike") / 100.0
    reset(conn)
    insert(conn, RUN_OLD, VALID_TIME, 1.1 * limit_m, SEGMENT_A)
    insert(conn, RUN_OLD, VALID_TIME, 0.9 * limit_m, SEGMENT_FAR, segment_id="way/1#0")
    assert band_ids(derive_areas(conn, VALID_TIME, "motorbike", RUN_OLD)) == ["b4", "b3"]


if __name__ == "__main__":
    raise SystemExit(main())
