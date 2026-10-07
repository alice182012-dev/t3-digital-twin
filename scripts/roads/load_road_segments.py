"""Loads the roads GeoJSON into road_segment: one row per road piece, keyed by a stable segment_id.

Usage: python load_road_segments.py [ROADS_GEOJSON]   (defaults to $ROADS_GEOJSON_PATH, then the
path dags/routing_adapter_dag.py uses)

Create the table first with scripts/database/create_road_segment_table.py.

A piece's segment_id is "<OSM way id>#<piece index>", for example "way/11835354#0". Each way is
cut into the fewest equal pieces no longer than the maximum piece length, measured in EPSG:3405,
so the same file and the same maximum always give the same ids.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ROADS_PATH = "/opt/airflow/data/mapping/inputs/toa-do-duong-hanoi.geojson"

# The choice and the numbers behind it are in artifacts/docs/concepts/road-segment-table.md.
DEFAULT_MAX_PIECE_M = 50.0
MAX_PIECE_ENV = "ROAD_SEGMENT_MAX_PIECE_M"

METRIC_SRID = 3405

# A way that is a whole multiple of the maximum, give or take float noise from the 4326 to 3405
# transform, should keep that many pieces. Without the slack, ceil() adds one more piece and every
# piece of the way shrinks (100.0001 m becomes three 33 m pieces instead of two 50 m pieces).
LENGTH_SLACK_M = 0.001


class RoadSegmentError(ValueError):
    pass


@dataclass(frozen=True)
class Way:
    way_id: str
    road_name: str | None
    highway: str | None
    geometry_json: str


@dataclass(frozen=True)
class LoadResult:
    inserted: int
    updated: int
    deleted: int
    total: int

    @property
    def changed(self) -> int:
        return self.inserted + self.updated + self.deleted


def max_piece_m() -> float:
    raw = os.getenv(MAX_PIECE_ENV)
    value = DEFAULT_MAX_PIECE_M if raw is None else float(raw)
    if value <= 0:
        raise RoadSegmentError(f"{MAX_PIECE_ENV} must be positive, got {raw!r}")
    return value


def parse_ways(feature_collection: dict) -> list[Way]:
    ways: list[Way] = []
    seen: set[str] = set()
    for index, feature in enumerate(feature_collection.get("features") or []):
        props = feature.get("properties") or {}
        way_id = props.get("@id")
        if not way_id:
            raise RoadSegmentError(f"feature {index} has no properties['@id']")
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "LineString":
            raise RoadSegmentError(
                f"feature {index} ({way_id}) is a {geometry.get('type')}, expected LineString"
            )
        if way_id in seen:
            raise RoadSegmentError(f"feature {index} repeats @id {way_id}")
        seen.add(way_id)
        ways.append(Way(way_id, props.get("name"), props.get("highway"), json.dumps(geometry)))
    if not ways:
        raise RoadSegmentError("roads file has no features")
    return ways


STAGE_WAYS_SQL = """
CREATE TEMP TABLE road_way_stage (
    way_id TEXT PRIMARY KEY,
    road_name TEXT,
    highway TEXT,
    geom_m geometry NOT NULL
) ON COMMIT DROP
"""

INSERT_WAYS_TEMPLATE = (
    "(%s, %s, %s, ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), "
    + str(METRIC_SRID)
    + "))"
)

STAGE_PIECES_SQL = """
CREATE TEMP TABLE road_piece_stage ON COMMIT DROP AS
SELECT w.way_id || '#' || i AS segment_id,
       w.way_id,
       i AS piece_index,
       w.road_name,
       w.highway,
       ST_Length(p.g) AS length_m,
       ST_Transform(p.g, 4326) AS geom
FROM (
    SELECT *, greatest(1, ceil((ST_Length(geom_m) - %(slack)s) / %(max_piece)s))::int AS n
    FROM road_way_stage
) w
CROSS JOIN LATERAL generate_series(0, w.n - 1) AS i
CROSS JOIN LATERAL (
    SELECT ST_LineSubstring(w.geom_m, i::float8 / w.n, (i + 1)::float8 / w.n) AS g
) p
"""

UPSERT_SQL = """
INSERT INTO road_segment (segment_id, way_id, piece_index, road_name, highway, length_m, geom)
SELECT segment_id, way_id, piece_index, road_name, highway, length_m, geom
FROM road_piece_stage
ON CONFLICT (segment_id) DO UPDATE SET
    way_id = EXCLUDED.way_id,
    piece_index = EXCLUDED.piece_index,
    road_name = EXCLUDED.road_name,
    highway = EXCLUDED.highway,
    length_m = EXCLUDED.length_m,
    geom = EXCLUDED.geom
WHERE (road_segment.road_name, road_segment.highway, road_segment.length_m, road_segment.geom)
    IS DISTINCT FROM (EXCLUDED.road_name, EXCLUDED.highway, EXCLUDED.length_m, EXCLUDED.geom)
RETURNING (xmax = 0) AS inserted
"""

DELETE_STALE_SQL = """
DELETE FROM road_segment r
WHERE NOT EXISTS (SELECT 1 FROM road_piece_stage s WHERE s.segment_id = r.segment_id)
"""


def load(conn, roads_path, max_piece: float | None = None) -> LoadResult:
    """Makes road_segment match roads_path in one transaction: upserts every piece and deletes
    every row the file no longer produces. Raises before writing anything on a feature with no
    @id, a non-LineString geometry, or a repeated @id, matching raster_load.load_run's posture."""
    max_piece = max_piece_m() if max_piece is None else max_piece
    with open(roads_path, encoding="utf-8") as f:
        ways = parse_ways(json.load(f))

    with conn, conn.cursor() as cur:
        cur.execute(STAGE_WAYS_SQL)
        execute_values(
            cur,
            "INSERT INTO road_way_stage (way_id, road_name, highway, geom_m) VALUES %s",
            [(w.way_id, w.road_name, w.highway, w.geometry_json) for w in ways],
            template=INSERT_WAYS_TEMPLATE,
            page_size=1000,
        )
        cur.execute(STAGE_PIECES_SQL, {"slack": LENGTH_SLACK_M, "max_piece": max_piece})
        cur.execute(UPSERT_SQL)
        written = [row[0] for row in cur.fetchall()]
        cur.execute(DELETE_STALE_SQL)
        deleted = cur.rowcount
        cur.execute("SELECT count(*) FROM road_segment")
        total = cur.fetchone()[0]

    inserted = sum(written)
    return LoadResult(inserted, len(written) - inserted, deleted, total)


def main() -> None:
    roads_path = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ROADS_GEOJSON_PATH", DEFAULT_ROADS_PATH)

    sys.path.insert(0, str(SCRIPTS_DIR / "database"))
    from db_config import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        started = time.monotonic()
        result = load(conn, roads_path)
        elapsed = time.monotonic() - started
    finally:
        conn.close()

    print(
        f"road_segment loaded from {roads_path} in {elapsed:.1f} s: "
        f"{result.inserted} inserted, {result.updated} updated, {result.deleted} deleted, "
        f"{result.total} rows total."
    )


if __name__ == "__main__":
    main()
