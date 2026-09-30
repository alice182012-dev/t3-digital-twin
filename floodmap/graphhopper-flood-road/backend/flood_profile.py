"""Flood depth at evenly spaced samples along a route, for POST /flood/profile.

Reads `flood_depth_raster_tile` for one (run, valid_time), the same table as flood_points.py and
flood_forecast.py. The frontend uses the samples to place the depth badges of the route.

Request body:

    {"points": [[lon, lat], ...], "valid_time": "2026-05-22T16:15:00+07:00", "run": "20260522T090000"}

`points` are the route's vertices, 1 to MAX_POINTS of them. `valid_time` needs a UTC offset. The
route is resampled by flood_forecast.sample_polyline, so a profile and a forecast of the same route
see the same points.

Response:

    {"samples": [{"lon", "lat", "depth_m"}, ...]}

in route order. `depth_m` is `null` for a sample outside the raster, and 0.0 for a sample inside it
whose pixel is 0 or NoData (see flood_points.classify), so dry never reads as missing.

Errors:

    400  body is not a JSON object, points missing, empty, or malformed
    400  valid_time missing, not ISO 8601, or without a UTC offset
    400  run missing or empty
    404  no raster for (run, valid_time)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from flood_forecast import parse_points, sample_polyline
from flood_points import FloodPointNotFound

_EXISTS_SQL = "SELECT EXISTS (SELECT 1 FROM flood_depth_raster_tile WHERE run_ts = %s AND valid_time_utc = %s);"

# ST_Value is non-NULL only on the tile that owns the sample's pixel, and a sample outside every
# tile gets no row from the lateral join, so its depth is NULL.
_PROFILE_SQL = """
WITH samples AS (
    SELECT s.ord, ST_SetSRID(ST_MakePoint(s.lon, s.lat), 4326) AS point
    FROM unnest(%(lons)s::float8[], %(lats)s::float8[]) WITH ORDINALITY AS s(lon, lat, ord)
)
SELECT s.ord,
       CASE WHEN px.raw IS NULL THEN NULL
            WHEN px.raw = px.nodata OR NOT px.raw > 0 THEN 0.0
            ELSE px.raw END AS depth
FROM samples s
LEFT JOIN LATERAL (
    SELECT v.raw, v.nodata
    FROM (
        SELECT ST_Value(t.rast, 1, s.point, false) AS raw, ST_BandNoDataValue(t.rast, 1) AS nodata
        FROM flood_depth_raster_tile t
        WHERE t.run_ts = %(run)s
          AND t.valid_time_utc = %(valid_time)s
          AND ST_Intersects(ST_ConvexHull(t.rast), s.point)
    ) v
    WHERE v.raw IS NOT NULL
    LIMIT 1
) px ON true
ORDER BY s.ord;
"""


@dataclass(frozen=True)
class ProfileQuery:
    points: tuple[tuple[float, float], ...]
    # Naive UTC, matching the TIMESTAMP column.
    valid_utc: datetime
    run: str


def parse_profile_body(body: object) -> ProfileQuery:
    """Raises ValueError, which server.py turns into a 400."""
    points = parse_points(body)

    raw_time = body.get("valid_time")
    if raw_time is None:
        raise ValueError("valid_time is required, for example 2026-05-22T16:15:00+07:00")
    try:
        valid_time = datetime.fromisoformat(raw_time) if isinstance(raw_time, str) else None
    except ValueError:
        valid_time = None
    if valid_time is None:
        raise ValueError(f"valid_time is not ISO 8601: {raw_time!r}")
    if valid_time.tzinfo is None:
        raise ValueError(f"valid_time needs a UTC offset, for example 2026-05-22T16:15:00+07:00: {raw_time!r}")

    run = body.get("run")
    if not isinstance(run, str) or not run:
        raise ValueError("run is required, for example 20260522T090000")

    return ProfileQuery(points, valid_time.astimezone(timezone.utc).replace(tzinfo=None), run)


def lookup_profile(conn, query: ProfileQuery) -> dict:
    samples = sample_polyline(query.points)
    params = {
        "lons": [lon for lon, _ in samples],
        "lats": [lat for _, lat in samples],
        "run": query.run,
        "valid_time": query.valid_utc,
    }
    with conn.cursor() as cur:
        cur.execute(_EXISTS_SQL, (query.run, query.valid_utc))
        if not cur.fetchone()[0]:
            raise FloodPointNotFound(f"no depth raster for run {query.run} at valid_time {query.valid_utc.isoformat()}")
        cur.execute(_PROFILE_SQL, params)
        rows = cur.fetchall()
    return {
        "samples": [
            {"lon": lon, "lat": lat, "depth_m": depth}
            for (lon, lat), (_, depth) in zip(samples, rows)
        ]
    }
