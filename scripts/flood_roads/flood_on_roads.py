"""Computes flood depth on every road piece from one run's raster tiles and writes it to
flood_road_values, the table routing reads (floodmap/graphhopper-flood-road/backend/flood_areas.py).

Usage: python flood_on_roads.py RUN_TS [--target TABLE]   (RUN_TS as the DAG names it, for example
20260924T164803)

Inputs are road_segment (scripts/roads/load_road_segments.py) and flood_depth_raster_tile
(scripts/flood_extent/raster_load.py). Each piece is sampled at the midpoint of every metre along
it, and `depth` is the deepest sample (decision D-006 in artifacts/docs/decisions/decision-log.md).
The design, its timings, and the row rules are in artifacts/docs/concepts/flood-on-roads.md.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2 import sql

SCRIPTS_DIR = Path(__file__).resolve().parents[1]

DEFAULT_TARGET = "flood_road_values"
SAMPLE_STEP_M = 1.0

# depth_*.tif names carry Vietnam local time, and flood_road_values keeps that local time naive
# (geojson_to_pg.py wrote the filename time as forecast_time). raster_load stores it as UTC.
VIETNAM_UTC_OFFSET = timedelta(hours=7)


@dataclass(frozen=True)
class TimestepResult:
    forecast_time: datetime
    rows: int
    wet_pieces: int
    sample_seconds: float


@dataclass(frozen=True)
class ComputeResult:
    run_ts: str
    target_table: str
    timesteps: tuple[TimestepResult, ...]
    seconds: float

    @property
    def rows(self) -> int:
        return sum(t.rows for t in self.timesteps)


class FloodOnRoadsError(ValueError):
    pass


def run_timestamp(run_ts: str) -> datetime:
    """Same format geojson_to_pg.parse_timestamp reads the run folder with."""
    return datetime.strptime(run_ts, "%Y%m%dT%H%M%S")


def create_shadow_table(conn, name: str) -> None:
    """A table shaped like flood_road_values, for comparing this task's output with the old rows
    without touching what routing reads. LIKE copies columns, defaults, and indexes, not the
    foreign key to flood_road_file."""
    with conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL("CREATE TABLE IF NOT EXISTS {} (LIKE flood_road_values INCLUDING ALL)").format(
                sql.Identifier(name)
            )
        )


_TIMESTEPS_SQL = """
SELECT DISTINCT valid_time_utc FROM flood_depth_raster_tile WHERE run_ts = %(run_ts)s ORDER BY 1
"""

_STAGE_SQL = """
CREATE TEMP TABLE piece_depth (
    valid_time_utc TIMESTAMP NOT NULL,
    segment_id TEXT NOT NULL,
    depth DOUBLE PRECISION NOT NULL
) ON COMMIT DROP
"""

# Each sample is matched to its pixel by grid arithmetic and an equality join on the wet pixels, so
# every tile is unpacked once. Calling ST_Value per sample unpacks the sample's 256 KB tile each time
# and gave the same numbers 12 times slower. Reading a tile's corner once in `tiles`, not once per
# wet pixel, halves the time again. The global grid comes from the tiles' own upper-left corners, so
# it does not depend on raster_load's tile size. Only pieces touching a tile with a wet pixel are
# sampled; every other piece is dry at this timestep.
_SAMPLE_SQL = """
WITH tiles AS MATERIALIZED (
    SELECT tile_x, tile_y, rast,
           ST_UpperLeftX(rast) AS tile_ulx, ST_UpperLeftY(rast) AS tile_uly
    FROM flood_depth_raster_tile
    WHERE run_ts = %(run_ts)s AND valid_time_utc = %(valid_time_utc)s
), grid AS MATERIALIZED (
    SELECT min(tile_ulx) AS ulx, max(tile_uly) AS uly,
           min(ST_ScaleX(rast)) AS sx, min(ST_ScaleY(rast)) AS sy
    FROM tiles
), wet_pixels AS MATERIALIZED (
    SELECT t.tile_x, t.tile_y,
           round((t.tile_ulx - g.ulx) / g.sx)::int + p.x - 1 AS gx,
           round((t.tile_uly - g.uly) / g.sy)::int + p.y - 1 AS gy,
           p.val AS depth
    FROM tiles t CROSS JOIN grid g
    CROSS JOIN LATERAL ST_PixelAsCentroids(t.rast, 1, true) p
    WHERE p.val > 0
), wet_tiles AS (
    SELECT DISTINCT tile_x, tile_y FROM wet_pixels
), candidates AS (
    SELECT DISTINCT r.segment_id, r.geom, r.length_m
    FROM tiles t
    JOIN wet_tiles USING (tile_x, tile_y)
    JOIN road_segment r ON ST_Intersects(r.geom, ST_ConvexHull(t.rast))
), samples AS (
    SELECT c.segment_id,
           floor((ST_X(pt) - g.ulx) / g.sx)::int AS gx,
           floor((ST_Y(pt) - g.uly) / g.sy)::int AS gy
    FROM (SELECT *, greatest(1, ceil(length_m / %(step)s))::int AS n FROM candidates) c
    CROSS JOIN LATERAL generate_series(0, c.n - 1) AS i
    CROSS JOIN LATERAL ST_LineInterpolatePoint(c.geom, (i + 0.5) / c.n) AS pt
    CROSS JOIN grid g
)
INSERT INTO piece_depth (valid_time_utc, segment_id, depth)
SELECT %(valid_time_utc)s, s.segment_id, max(coalesce(w.depth, 0))
FROM samples s LEFT JOIN wet_pixels w USING (gx, gy)
GROUP BY s.segment_id
"""

_REGISTER_SQL = """
INSERT INTO flood_road_file (timestamp, source_file, geojson_type, feature_count)
VALUES (%(timestamp)s, %(source_file)s, NULL, %(feature_count)s)
ON CONFLICT (source_file) DO UPDATE SET
    timestamp = EXCLUDED.timestamp,
    geojson_type = EXCLUDED.geojson_type,
    feature_count = EXCLUDED.feature_count
RETURNING id
"""

_DELETE_SQL = """
DELETE FROM {target} WHERE timestamp = %(timestamp)s AND forecast_time = ANY(%(forecast_times)s)
"""

# A piece wet at any timestep of the run gets a row at every timestep, 0 where it is dry. routing's
# winner run for a forecast_time is the newest run with rows at that time, and flood_metrics reads
# each piece's full series.
_INSERT_SQL = """
WITH wet AS (
    SELECT segment_id FROM piece_depth GROUP BY segment_id HAVING max(depth) > 0
), steps (valid_time_utc) AS (
    SELECT unnest(%(valid_times)s::timestamp[])
)
INSERT INTO {target}
    (file_id, timestamp, road_name, forecast_time, depth, segment_id, geom, geom_4326)
SELECT %(file_id)s, %(timestamp)s, coalesce(r.road_name, r.way_id),
       s.valid_time_utc + %(offset)s,
       coalesce(d.depth, 0), r.segment_id,
       ST_AsGeoJSON(r.geom)::jsonb, r.geom
FROM wet
JOIN road_segment r USING (segment_id)
CROSS JOIN steps s
LEFT JOIN piece_depth d ON d.segment_id = wet.segment_id AND d.valid_time_utc = s.valid_time_utc
"""

_COUNT_SQL = """
SELECT valid_time_utc,
       count(*) FILTER (WHERE depth > 0)
FROM piece_depth GROUP BY valid_time_utc
"""


def compute(conn, run_ts: str, target_table: str = DEFAULT_TARGET) -> ComputeResult:
    """Replaces every row of (run timestamp, forecast_time) for this run's timesteps in one
    transaction, so a retry converges on the same rows. Raises when the run has no tiles, since an
    empty write would hand routing's winner for those times to an older run."""
    started = time.monotonic()
    timestamp = run_timestamp(run_ts)
    target = sql.Identifier(target_table)
    with conn, conn.cursor() as cur:
        # Two concurrent writers of one run would each delete only committed rows and then both
        # insert, leaving duplicates.
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"{target_table}/{run_ts}",))
        cur.execute(_TIMESTEPS_SQL, {"run_ts": run_ts})
        valid_times = [row[0] for row in cur.fetchall()]
        if not valid_times:
            raise FloodOnRoadsError(f"no flood_depth_raster_tile rows for run {run_ts}")

        cur.execute(_STAGE_SQL)
        sample_seconds = {}
        for valid_time in valid_times:
            step_started = time.monotonic()
            cur.execute(
                _SAMPLE_SQL, {"run_ts": run_ts, "valid_time_utc": valid_time, "step": SAMPLE_STEP_M}
            )
            sample_seconds[valid_time] = time.monotonic() - step_started

        cur.execute(_COUNT_SQL)
        wet_by_time = dict(cur.fetchall())
        cur.execute("SELECT count(DISTINCT segment_id) FROM piece_depth WHERE depth > 0")
        piece_rows = cur.fetchone()[0]

        cur.execute(
            _REGISTER_SQL,
            {"timestamp": timestamp, "source_file": f"flood_on_roads_{run_ts}", "feature_count": piece_rows},
        )
        file_id = cur.fetchone()[0]
        forecast_times = [v + VIETNAM_UTC_OFFSET for v in valid_times]
        cur.execute(
            sql.SQL(_DELETE_SQL).format(target=target),
            {"timestamp": timestamp, "forecast_times": forecast_times},
        )
        cur.execute(
            sql.SQL(_INSERT_SQL).format(target=target),
            {
                "file_id": file_id,
                "timestamp": timestamp,
                "valid_times": valid_times,
                "offset": VIETNAM_UTC_OFFSET,
            },
        )

    return ComputeResult(
        run_ts=run_ts,
        target_table=target_table,
        timesteps=tuple(
            TimestepResult(
                forecast_time=v + VIETNAM_UTC_OFFSET,
                rows=piece_rows,
                wet_pieces=wet_by_time.get(v, 0),
                sample_seconds=sample_seconds[v],
            )
            for v in valid_times
        ),
        seconds=time.monotonic() - started,
    )


def main(argv: list[str] | None = None) -> ComputeResult:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_ts")
    parser.add_argument("--target", default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(SCRIPTS_DIR / "database"))
    from db_config import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        if args.target != DEFAULT_TARGET:
            create_shadow_table(conn, args.target)
        result = compute(conn, args.run_ts, args.target)
    finally:
        conn.close()

    for step in result.timesteps:
        print(
            f"{step.forecast_time:%Y-%m-%d %H:%M:%S}: {step.rows} rows, "
            f"{step.wet_pieces} wet pieces, sampled in {step.sample_seconds:.1f} s"
        )
    print(f"{result.rows} rows written to {result.target_table} for {result.run_ts} in {result.seconds:.1f} s.")
    return result


if __name__ == "__main__":
    main()
