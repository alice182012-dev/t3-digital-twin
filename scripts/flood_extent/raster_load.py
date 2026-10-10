"""Loads calculate_depth.py's per-timestep depth.tif files into PostGIS as queryable raster tiles.

GET /flood/points needs the exact depth at an arbitrary lat/lon, which flood_road_values (depth at
road segments only) and flood_extent_polygon (banded ranges only) can't answer. depth.tif is
always the source of truth for depth values, so this loads it into `flood_depth_raster_tile`,
cut into TILE_SIZE x TILE_SIZE tiles. A whole timestep is about 10000 x 5500 pixels (209 MB
decoded), and ST_Value on a one-row raster unpacks all of it per lookup; a lookup that selects
its tile through the GIST index on ST_ConvexHull(rast) unpacks 256 KB.

depth.tif ships in the 3Di simulation's own projected CRS (VN-2000 / UTM zone 48N, EPSG:3405; see
flood_areas.py's ST_Transform(v.geom_4326, 3405) for the same SRID elsewhere in this codebase),
not EPSG:4326. flood_extent.py's reprojection_to_4326 handles the same mismatch for its vectorized
polygon output; this module reprojects the raster itself, once, at load time, so a point-depth
query never needs its own transform.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from osgeo import gdal

import flood_extent
import publish
import run_output

gdal.UseExceptions()

TARGET_SRID = 4326
# 128 and 256 tied on lookup time for the real depth.tif (about 0.1 ms warm, 0.8 ms with the
# tile evicted from shared_buffers); 512 was twice as slow warm. 256 writes 4x fewer rows than 128.
TILE_SIZE = 256
DEFAULT_KEEP_RUNS = 8

_DELETE_TIMESTEP_SQL = """
DELETE FROM flood_depth_raster_tile
WHERE run_ts = %(run_ts)s AND valid_time_utc = %(valid_time_utc)s
"""

# Tiles are unpadded, so each hull is the tile's real extent. The position comes from each
# tile's own origin, rounded, so it doesn't depend on the order ST_Tile emits tiles in.
_INSERT_TILES_SQL = """
WITH src AS (SELECT ST_FromGDALRaster(%(data)s, %(srid)s) AS rast)
INSERT INTO flood_depth_raster_tile (run_ts, valid_time_utc, tile_x, tile_y, rast)
SELECT %(run_ts)s,
       %(valid_time_utc)s,
       round((ST_UpperLeftX(t.rast) - ST_UpperLeftX(src.rast)) / (ST_ScaleX(src.rast) * %(size)s))::int,
       round((ST_UpperLeftY(t.rast) - ST_UpperLeftY(src.rast)) / (ST_ScaleY(src.rast) * %(size)s))::int,
       t.rast
FROM src, LATERAL ST_Tile(src.rast, %(size)s, %(size)s) AS t(rast)
"""


def reproject_to_4326(src_path: Path, dst_path: Path) -> None:
    ds = gdal.Warp(str(dst_path), str(src_path), dstSRS=f"EPSG:{TARGET_SRID}", resampleAlg="near")
    if ds is None:
        raise flood_extent.FloodExtentError(f"gdal.Warp produced no output for {src_path}")
    ds = None  # noqa: F841 (closes/flushes the GDAL dataset)


def write_tiles(cur, run_ts: str, valid_time_utc, raster_path: Path) -> None:
    """Replaces every tile of (run_ts, valid_time_utc). The caller owns the transaction, so a retried
    load converges on the same rows instead of mixing tiles from two attempts."""
    data = Path(raster_path).read_bytes()
    params = {
        "run_ts": run_ts,
        "valid_time_utc": valid_time_utc,
        "data": psycopg2.Binary(data),
        "srid": TARGET_SRID,
        "size": TILE_SIZE,
    }
    # postgis.gdal_enabled_drivers defaults to DISABLE_ALL (PostGIS disables every out-db
    # GDAL driver unless a session opts in), so ST_FromGDALRaster otherwise fails with
    # "Could not open bytea with GDAL" on a perfectly valid GeoTIFF. Session-scoped, no
    # superuser or server restart needed.
    cur.execute("SET postgis.gdal_enabled_drivers = 'GTiff';")
    cur.execute(_DELETE_TIMESTEP_SQL, params)
    cur.execute(_INSERT_TILES_SQL, params)


def prune_raster_runs(cur, keep_runs: int, always_keep: str) -> list[str]:
    """Deletes every tile of runs outside the newest `keep_runs` by run_ts, never `always_keep`.
    Returns the pruned runs. Same posture as publish.prune_bucket_runs: run_ts is a fixed-width
    YYYYMMDDTHHMMSS string, so its lexical order is its time order."""
    cur.execute("SELECT DISTINCT run_ts FROM flood_depth_raster_tile ORDER BY run_ts DESC;")
    runs = [row[0] for row in cur.fetchall()]
    old_runs = [run for run in runs[keep_runs:] if run != always_keep]
    if old_runs:
        cur.execute("DELETE FROM flood_depth_raster_tile WHERE run_ts = ANY(%s);", (old_runs,))
    return old_runs


def load_run(conn, depth_dir, run_ts: str, work_dir, keep_runs: int | None = None) -> list:
    """Reprojects and loads every depth_*.tif in depth_dir, one transaction per timestep. The last
    timestep's transaction also prunes runs older than the newest `keep_runs`, or
    FLOOD_RASTER_KEEP_RUNS (default 8) when it is None, and records the run's `depth_raster` row in
    flood_run_output, so the row commits only with every tile of the run. Returns the list of
    valid_time_utc values loaded. Fails loudly (raises) on the first bad file, matching
    publish.publish_run's posture: a partial load is safer to investigate than to hide behind a
    best-effort continue."""
    if keep_runs is None:
        keep_runs = int(os.environ.get("FLOOD_RASTER_KEEP_RUNS", DEFAULT_KEEP_RUNS))
    if keep_runs < 1:
        raise ValueError(f"keep_runs must be at least 1: {keep_runs}")
    depth_dir = Path(depth_dir)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    depth_files = sorted(p for p in depth_dir.iterdir() if flood_extent.DEPTH_FILE.match(p.name))
    if not depth_files:
        raise flood_extent.FloodExtentError(f"No depth_*.tif files in {depth_dir}")

    loaded = []
    for depth_file in depth_files:
        valid_time = publish.valid_time_utc(depth_file.name)
        # Overlapping runs share valid times on the 15-minute grid, so the name carries run_ts.
        reprojected = work_dir / f"{run_ts}_{depth_file.stem}_4326.tif"
        try:
            reproject_to_4326(depth_file, reprojected)
            with conn, conn.cursor() as cur:
                write_tiles(cur, run_ts, valid_time, reprojected)
                if depth_file == depth_files[-1]:
                    prune_raster_runs(cur, keep_runs, always_keep=run_ts)
                    run_output.record(cur, run_ts, run_output.Output.DEPTH_RASTER)
            loaded.append(valid_time)
        finally:
            reprojected.unlink(missing_ok=True)
    return loaded
