"""Loads calculate_depth.py's per-timestep depth.tif files into PostGIS as queryable rasters.

Story 2 of artifacts/docs/user-stories/point-depth-lookup-backend.md: GET /flood/points (Sprint 2)
needs the exact depth at an arbitrary lat/lon, which flood_road_values (depth at road segments
only) and flood_extent_polygon (banded ranges only) can't answer. depth.tif is always the source
of truth for depth values, so this loads it directly and makes it queryable with
`ST_Value(rast, ST_SetSRID(ST_MakePoint(lon, lat), 4326))`, without reading the file from disk on
every request.

depth.tif ships in the 3Di simulation's own projected CRS (VN-2000 / UTM zone 48N, EPSG:3405; see
flood_areas.py's ST_Transform(v.geom_4326, 3405) for the same SRID elsewhere in this codebase),
not EPSG:4326. flood_extent.py's reprojection_to_4326 handles the same mismatch for its vectorized
polygon output; this module reprojects the raster itself, once, at load time, so a point-depth
query never needs its own transform.
"""

from __future__ import annotations

from pathlib import Path

import psycopg2
from osgeo import gdal

import flood_extent
import publish

gdal.UseExceptions()

TARGET_SRID = 4326


def reproject_to_4326(src_path: Path, dst_path: Path) -> None:
    ds = gdal.Warp(str(dst_path), str(src_path), dstSRS=f"EPSG:{TARGET_SRID}", resampleAlg="near")
    if ds is None:
        raise flood_extent.FloodExtentError(f"gdal.Warp produced no output for {src_path}")
    ds = None  # noqa: F841 (closes/flushes the GDAL dataset)


def load_raster(conn, run_ts: str, valid_time_utc, raster_path: Path) -> None:
    """Upserts one row: same (run_ts, valid_time_utc) replaces its own raster instead of
    duplicating it, matching publish.write_polygon_rows' retry-safe upsert for the same run."""
    with open(raster_path, "rb") as f:
        data = f.read()
    with conn.cursor() as cur:
        # postgis.gdal_enabled_drivers defaults to DISABLE_ALL (PostGIS disables every out-db
        # GDAL driver unless a session opts in), so ST_FromGDALRaster otherwise fails with
        # "Could not open bytea with GDAL" on a perfectly valid GeoTIFF. Session-scoped, no
        # superuser or server restart needed.
        cur.execute("SET postgis.gdal_enabled_drivers = 'GTiff';")
        cur.execute(
            """
            INSERT INTO flood_depth_raster (run_ts, valid_time_utc, rast)
            VALUES (%(run_ts)s, %(valid_time_utc)s, ST_FromGDALRaster(%(data)s, %(srid)s))
            ON CONFLICT (run_ts, valid_time_utc)
            DO UPDATE SET rast = EXCLUDED.rast
            """,
            {
                "run_ts": run_ts,
                "valid_time_utc": valid_time_utc,
                "data": psycopg2.Binary(data),
                "srid": TARGET_SRID,
            },
        )
    conn.commit()


def load_run(conn, depth_dir, run_ts: str, work_dir) -> list:
    """Reprojects and loads every depth_*.tif in depth_dir. Returns the list of valid_time_utc
    values loaded. Fails loudly (raises) on the first bad file, matching publish.publish_run's
    posture: a partial load is safer to investigate than to hide behind a best-effort continue."""
    depth_dir = Path(depth_dir)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    depth_files = sorted(p for p in depth_dir.iterdir() if flood_extent.DEPTH_FILE.match(p.name))
    if not depth_files:
        raise flood_extent.FloodExtentError(f"No depth_*.tif files in {depth_dir}")

    loaded = []
    for depth_file in depth_files:
        valid_time = publish.valid_time_utc(depth_file.name)
        reprojected = work_dir / f"{depth_file.stem}_4326.tif"
        try:
            reproject_to_4326(depth_file, reprojected)
            load_raster(conn, run_ts, valid_time, reprojected)
            loaded.append(valid_time)
        finally:
            reprojected.unlink(missing_ok=True)
    return loaded
