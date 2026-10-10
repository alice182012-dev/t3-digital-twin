"""Writes a run's first depth rasters back out of `flood_depth_raster_tile` as depth_*.tif files.

The tile build (publish.publish_run) reads depth_*.tif files. The `flood_tiles` DAG normally reads the files that
task 3 wrote. With FLOOD_TILES_INPUT=postgis it reads the table instead, so the tile build needs no shared disk with
the worker. The exported files are in EPSG:4326, the SRID that raster_load stores, and they are named from the
Vietnam local time of the step, the same naming as calculate_depth.py, so publish.valid_time_utc and
flood_extent.stamp_key give the same keys as for the original files.
"""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

import publish

_STEPS_SQL = """
SELECT DISTINCT valid_time_utc FROM flood_depth_raster_tile
WHERE run_ts = %(run_ts)s
ORDER BY valid_time_utc
LIMIT %(steps)s
"""

# ST_Union of the unpadded tiles rebuilds the whole timestep. ST_AsGDALRaster needs the GTiff driver enabled for
# the session, as raster_load.write_tiles does for ST_FromGDALRaster.
_RASTER_SQL = """
SELECT ST_AsGDALRaster(ST_Union(rast), 'GTiff')
FROM flood_depth_raster_tile
WHERE run_ts = %(run_ts)s AND valid_time_utc = %(valid_time_utc)s
"""


def depth_filename(valid_time_utc) -> str:
    """The UTC instant of a step -> depth_YYYYMMDD_HHMMSS.tif in Vietnam local time."""
    if valid_time_utc.tzinfo is None:
        valid_time_utc = valid_time_utc.replace(tzinfo=timezone.utc)
    local = valid_time_utc + publish.VIETNAM_UTC_OFFSET
    return f"depth_{local:%Y%m%d_%H%M%S}.tif"


def export_run(conn, run_ts: str, out_dir, steps: int) -> list[Path]:
    """Writes the first `steps` timesteps of `run_ts`, by time, into `out_dir` and returns the files.

    Raises ValueError when the run has no rows, so a run that is not loaded fails loudly instead of building nothing.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with conn, conn.cursor() as cur:
        cur.execute("SET postgis.gdal_enabled_drivers = 'GTiff';")
        cur.execute(_STEPS_SQL, {"run_ts": run_ts, "steps": steps})
        valid_times = [row[0] for row in cur.fetchall()]
        if not valid_times:
            raise ValueError(f"❌ Run {run_ts} has no rows in flood_depth_raster_tile")
        for valid_time in valid_times:
            cur.execute(_RASTER_SQL, {"run_ts": run_ts, "valid_time_utc": valid_time})
            path = out_dir / depth_filename(valid_time)
            path.write_bytes(bytes(cur.fetchone()[0]))
            written.append(path)
    return written
