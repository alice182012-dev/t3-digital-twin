"""Exact flood depth at one lat/lon and timestep, for GET /flood/points.

Reads `flood_depth_raster` (run_ts, valid_time_utc, rast in EPSG:4326), which
scripts/flood_extent/raster_load.py fills from each run's depth_*.tif. See Story 3 of
artifacts/docs/user-stories/point-depth-lookup-backend.md.

Run selection matches flood_extent_runs.list_timesteps: an explicit `run` pins that run, and
"latest" resolves to flood_extent_runs.latest_run(), the newest run overall. A valid_time the
newest run lacks is a 404, never a fallback to an older run that has it, so the depth always
belongs to the same single-run series the map's timestep picker shows.

Response `status` values:

    wet      depth_m > 0, the raster value at the point
    dry      depth_m = 0.0, the point is inside the raster but its pixel is 0 or NoData
    no_data  depth_m = null, the point is outside the raster extent

Errors:

    400  lat or lon missing, not a number, or out of range
    400  valid_time missing, not ISO 8601, or without a UTC offset
    404  no run loaded, or no raster for (run, valid_time)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from flood_extent_runs import latest_run

PointStatus = Literal["wet", "dry", "no_data"]

_POINT_VALUE_SQL = """
SELECT ST_Value(rast, 1, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326), false),
       ST_BandNoDataValue(rast, 1)
FROM flood_depth_raster
WHERE run_ts = %(run)s AND valid_time_utc = %(valid_time_utc)s;
"""


class FloodPointNotFound(Exception):
    pass


@dataclass(frozen=True)
class PointQuery:
    lat: float
    lon: float
    valid_time: str
    # Naive UTC, the same reading flood_extent_runs.list_timesteps gives the TIMESTAMP column.
    valid_time_utc: datetime
    run: str


@dataclass(frozen=True)
class PointDepth:
    status: PointStatus
    depth_m: float | None


def parse_point_query(qs: dict[str, list[str]]) -> PointQuery:
    """Raises ValueError, which server.py turns into a 400."""
    valid_time = qs.get("valid_time", [""])[0]
    if not valid_time:
        raise ValueError("valid_time is required")
    try:
        parsed = datetime.fromisoformat(valid_time)
    except ValueError:
        raise ValueError(f"valid_time is not ISO 8601: {valid_time!r}") from None
    if parsed.tzinfo is None:
        raise ValueError(f"valid_time needs a UTC offset, for example 2026-05-22T16:00:00+07:00: {valid_time!r}")

    return PointQuery(
        lat=_coordinate(qs, "lat", 90.0),
        lon=_coordinate(qs, "lon", 180.0),
        valid_time=valid_time,
        valid_time_utc=parsed.astimezone(timezone.utc).replace(tzinfo=None),
        run=qs.get("run", ["latest"])[0] or "latest",
    )


def _coordinate(qs: dict[str, list[str]], name: str, limit: float) -> float:
    raw = qs.get(name, [""])[0]
    if not raw:
        raise ValueError(f"{name} is required")
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} is not a number: {raw!r}") from None
    if not math.isfinite(value) or abs(value) > limit:
        raise ValueError(f"{name} must be between -{limit:g} and {limit:g}: {raw!r}")
    return value


def classify(raw: float | None, nodata: float | None) -> PointDepth:
    if raw is None:
        return PointDepth("no_data", None)
    # calculate_depth.py rewrites NoData, negative, and out-of-range pixels to 0 and then
    # declares 0 as NoData, so inside the raster the source can't tell a dry cell from an
    # unmodeled one. Both read as dry; only a point outside the raster is detectably no_data.
    if raw == nodata or not raw > 0:
        return PointDepth("dry", 0.0)
    return PointDepth("wet", raw)


def lookup_point_depth(conn, query: PointQuery) -> dict:
    run = query.run if query.run != "latest" else latest_run(conn)
    if run is None:
        raise FloodPointNotFound("no flood run is loaded")
    with conn.cursor() as cur:
        cur.execute(
            _POINT_VALUE_SQL,
            {"lat": query.lat, "lon": query.lon, "run": run, "valid_time_utc": query.valid_time_utc},
        )
        row = cur.fetchone()
    if row is None:
        raise FloodPointNotFound(f"no depth raster for run {run} at valid_time {query.valid_time}")
    depth = classify(*row)
    return {
        "lat": query.lat,
        "lon": query.lon,
        "valid_time": query.valid_time,
        "run": run,
        "status": depth.status,
        "depth_m": depth.depth_m,
    }
