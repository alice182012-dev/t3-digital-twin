"""Flood depth over time along a route, for POST /flood/forecast.

Reads `flood_depth_raster_tile` (run_ts, valid_time_utc, one EPSG:4326 tile per row), the same
table as flood_points.py, which holds every depth step of every retained run. flood_road_values is
not used: it only covers road segments, and matching a route to its rows has no stable key.

Request body:

    {"points": [[lon, lat], ...], "from": "2026-05-22T16:00:00+07:00", "steps": 8}

`points` are the route's vertices, 1 to MAX_POINTS of them. `from` defaults to now, floored to
15 minutes. The window is the half-open interval [from, from + steps * 15 min).

Sampling. Route vertices are uneven: a straight road has two, a bend has dozens, so a mean over
vertices would weight bends. The route is resampled every SAMPLE_SPACING_M metres of
great-circle length, endpoints included. A route longer than
SAMPLE_SPACING_M * (MAX_SAMPLES - 1) gets MAX_SAMPLES evenly spaced samples instead, which bounds
the query at MAX_SAMPLES * steps raster lookups.

Run selection. Each valid_time in the window takes the newest run (max run_ts) that has a raster
for it, so consecutive columns can carry different runs. A valid_time with no raster in any run
is omitted.

Response:

    {"columns": [{"valid_time", "run", "mean_depth_m", "max_depth_m", "wet_fraction"}, ...]}

ascending by valid_time, which carries a +07:00 offset like GET /flood/timesteps. Samples outside
the raster are left out of all three figures. A sample inside the raster whose pixel is 0 or NoData
counts as dry, depth 0 (see flood_points.classify). When no sample is inside the raster, all three
figures are null.

Errors:

    400  body is not a JSON object, or points missing, empty, or longer than MAX_POINTS
    400  a point is not [lon, lat] numbers in range
    400  from is not ISO 8601 or has no UTC offset
    400  steps is not an integer from 1 to MAX_STEPS
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from flood_extent_runs import VIETNAM_TZ

MAX_POINTS = 2000
MAX_STEPS = 96
DEFAULT_STEPS = 8
STEP = timedelta(minutes=15)
SAMPLE_SPACING_M = 25.0
MAX_SAMPLES = 200
_EARTH_RADIUS_M = 6371008.8

# One lookup per (sample, step). A sample on a shared tile edge intersects up to four hulls, but
# ST_Value is non-NULL only on the tile that owns its pixel; a sample outside every tile gets no
# row from the lateral join, and so no value.
_FORECAST_SQL = """
WITH samples AS (
    SELECT ST_SetSRID(ST_MakePoint(lon, lat), 4326) AS point
    FROM unnest(%(lons)s::float8[], %(lats)s::float8[]) AS s(lon, lat)
),
steps AS (
    SELECT valid_time_utc, max(run_ts) AS run_ts
    FROM flood_depth_raster_tile
    WHERE valid_time_utc >= %(start)s AND valid_time_utc < %(end)s
    GROUP BY valid_time_utc
),
depths AS (
    SELECT st.valid_time_utc, st.run_ts,
           CASE WHEN px.raw = px.nodata OR NOT px.raw > 0 THEN 0.0 ELSE px.raw END AS depth
    FROM steps st
    CROSS JOIN samples s
    LEFT JOIN LATERAL (
        SELECT v.raw, v.nodata
        FROM (
            SELECT ST_Value(t.rast, 1, s.point, false) AS raw, ST_BandNoDataValue(t.rast, 1) AS nodata
            FROM flood_depth_raster_tile t
            WHERE t.run_ts = st.run_ts
              AND t.valid_time_utc = st.valid_time_utc
              AND ST_Intersects(ST_ConvexHull(t.rast), s.point)
        ) v
        WHERE v.raw IS NOT NULL
        LIMIT 1
    ) px ON true
)
SELECT valid_time_utc, run_ts, avg(depth), max(depth),
       count(*) FILTER (WHERE depth > 0)::float8 / nullif(count(depth), 0)
FROM depths
GROUP BY valid_time_utc, run_ts
ORDER BY valid_time_utc;
"""


@dataclass(frozen=True)
class ForecastQuery:
    points: tuple[tuple[float, float], ...]
    # Naive UTC, matching the TIMESTAMP column.
    start_utc: datetime
    steps: int


def floor_to_step(moment: datetime) -> datetime:
    """Floors an aware datetime to the 15-minute grid, in UTC."""
    utc = moment.astimezone(timezone.utc)
    return utc - timedelta(minutes=utc.minute % 15, seconds=utc.second, microseconds=utc.microsecond)


def parse_forecast_body(body: object, now: datetime) -> ForecastQuery:
    """Raises ValueError, which server.py turns into a 400. `now` is aware."""
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")

    raw_points = body.get("points")
    if not isinstance(raw_points, list) or not raw_points:
        raise ValueError("points is required: a list of [lon, lat]")
    if len(raw_points) > MAX_POINTS:
        raise ValueError(f"points has {len(raw_points)} entries, at most {MAX_POINTS} are allowed")
    points = tuple(_point(raw, i) for i, raw in enumerate(raw_points))

    raw_from = body.get("from")
    if raw_from is None:
        start = floor_to_step(now)
    else:
        try:
            start = datetime.fromisoformat(raw_from) if isinstance(raw_from, str) else None
        except ValueError:
            start = None
        if start is None:
            raise ValueError(f"from is not ISO 8601: {raw_from!r}")
        if start.tzinfo is None:
            raise ValueError(f"from needs a UTC offset, for example 2026-05-22T16:00:00+07:00: {raw_from!r}")

    steps = body.get("steps", DEFAULT_STEPS)
    if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= MAX_STEPS:
        raise ValueError(f"steps must be an integer from 1 to {MAX_STEPS}: {steps!r}")

    return ForecastQuery(points, start.astimezone(timezone.utc).replace(tzinfo=None), steps)


def _point(raw: object, index: int) -> tuple[float, float]:
    if (
        not isinstance(raw, list)
        or len(raw) < 2
        or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in raw[:2])
    ):
        raise ValueError(f"points[{index}] must be [lon, lat]: {raw!r}")
    lon, lat = float(raw[0]), float(raw[1])
    if not (math.isfinite(lon) and math.isfinite(lat) and abs(lon) <= 180 and abs(lat) <= 90):
        raise ValueError(f"points[{index}] is out of range: {raw!r}")
    return lon, lat


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def sample_polyline(points: tuple[tuple[float, float], ...]) -> list[tuple[float, float]]:
    """Evenly spaced samples along the polyline by length, endpoints included (see module doc).
    Positions within a segment are interpolated linearly in lon/lat, which is exact enough over
    the tens of metres between samples."""
    lengths = [_haversine_m(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    if total == 0:
        return [points[0]]
    count = min(MAX_SAMPLES, math.ceil(total / SAMPLE_SPACING_M) + 1)
    samples = []
    segment, walked = 0, 0.0
    for i in range(count):
        target = total * i / (count - 1)
        while segment < len(lengths) - 1 and walked + lengths[segment] < target:
            walked += lengths[segment]
            segment += 1
        (lon1, lat1), (lon2, lat2) = points[segment], points[segment + 1]
        fraction = min(1.0, (target - walked) / lengths[segment]) if lengths[segment] else 0.0
        samples.append((lon1 + (lon2 - lon1) * fraction, lat1 + (lat2 - lat1) * fraction))
    return samples


def lookup_forecast(conn, query: ForecastQuery) -> dict:
    samples = sample_polyline(query.points)
    params = {
        "lons": [lon for lon, _ in samples],
        "lats": [lat for _, lat in samples],
        "start": query.start_utc,
        "end": query.start_utc + query.steps * STEP,
    }
    with conn.cursor() as cur:
        cur.execute(_FORECAST_SQL, params)
        rows = cur.fetchall()
    return {
        "columns": [
            {
                "valid_time": valid_time.replace(tzinfo=timezone.utc).astimezone(VIETNAM_TZ).isoformat(),
                "run": run,
                "mean_depth_m": mean,
                "max_depth_m": deepest,
                "wet_fraction": wet_fraction,
            }
            for valid_time, run, mean, deepest, wet_fraction in rows
        ]
    }
