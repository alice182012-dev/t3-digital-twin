"""PostGIS-derived flood polygons for a (run, valid_time, vehicle) cell.

Single source of truth for the custom_model.areas gate GraphHopper actually
routes against (POST /route) and the equivalent map overlay (GET
/flood/areas) — see Workstream A/B of the Phase 2 plan. Buffer/simplify/
min-area defaults match the values Phase A's D2 sweep validated (buffer=22m,
min_area=400m2).

Reads `edge_depth`, the wet edges the routing engine's own table is built from, and takes their
geometry from `graph_edge`, so the map and the engine see the same water. The run that wins a forecast
time is the newest run in `edge_depth_run` whose `valid_times` contains it, so a run with no wet edge
still wins.
It is a separate table and pipeline from
`flood_extent_polygon` (see flood_extent_runs.py, which backs the map's
timestep picker). See artifacts/raw/T3-Digital-Twin_Architecture.md section 4.2 for why routing and
map-display visualization intentionally read different flood tables.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from flood_utils import depth_bands_m

DEFAULT_BUFFER_M = 22.0
DEFAULT_SIMPLIFY_M = 3.0
DEFAULT_MIN_AREA_M2 = 400.0

VIETNAM_TZ = timezone(timedelta(hours=7))

_SEG_SQL = """
WITH winner AS (
    {winner_select}
), seg AS (
    SELECT ST_Transform(e.geom, 3405) AS g
    FROM edge_depth d
    JOIN winner w USING (run_ts)
    JOIN graph_edge e USING (edge_key)
    WHERE d.valid_time_utc = %(valid_time_utc)s
      AND d.depth_cm >= %(band_min_cm)s {band_max_clause}
), parts AS (
    SELECT (ST_Dump(ST_Union(ST_Buffer(g, %(buffer_m)s)))).geom AS g FROM seg
)
SELECT ST_AsGeoJSON(ST_Transform(ST_SimplifyPreserveTopology(g, %(simplify_m)s), 4326), 6)
FROM parts WHERE ST_Area(g) >= %(min_area_m2)s;
"""

_LATEST_WINNER = "SELECT max(run_ts) AS run_ts FROM edge_depth_run WHERE %(valid_time_utc)s = ANY(valid_times)"
_PINNED_WINNER = "SELECT %(run)s::text AS run_ts"


def _utc_naive(valid_time: str) -> datetime:
    """The UTC clock time of a request's valid_time, the form edge_depth stores. A time with no offset
    is Vietnam local time, as in the other tables of the contract."""
    parsed = datetime.fromisoformat(valid_time)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=VIETNAM_TZ)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def derive_areas(
    conn,
    valid_time: str,
    vehicle_type: str = "motorbike",
    run: str = "latest",
    buffer_m: float = DEFAULT_BUFFER_M,
    simplify_m: float = DEFAULT_SIMPLIFY_M,
    min_area_m2: float = DEFAULT_MIN_AREA_M2,
) -> dict[str, Any]:
    """Returns a GeoJSON FeatureCollection, one Feature per flooded polygon,
    ordered deepest-band-first. Each feature's properties carry `band` and
    `multiply_by` so build_custom_model() can turn this straight into
    custom_model.priority without re-deriving anything."""
    features: list[dict[str, Any]] = []
    pinned = bool(run) and run != "latest"
    winner_select = _PINNED_WINNER if pinned else _LATEST_WINNER
    valid_time_utc = _utc_naive(valid_time)

    with conn.cursor() as cur:
        for band in depth_bands_m(vehicle_type):
            band_max_clause = "AND d.depth_cm < %(band_max_cm)s" if band["band_max"] is not None else ""
            sql = _SEG_SQL.format(winner_select=winner_select, band_max_clause=band_max_clause)
            params = {
                "valid_time_utc": valid_time_utc,
                "run": run,
                "band_min_cm": round(band["band_min"] * 100),
                "band_max_cm": None if band["band_max"] is None else round(band["band_max"] * 100),
                "buffer_m": buffer_m,
                "simplify_m": simplify_m,
                "min_area_m2": min_area_m2,
            }
            cur.execute(sql, params)
            for index, (geojson_text,) in enumerate(cur.fetchall(), start=1):
                features.append(
                    {
                        "type": "Feature",
                        "id": f"{band['id']}_{index}",
                        "geometry": _parse_geojson(geojson_text),
                        "properties": {
                            "band": band["id"],
                            "multiply_by": band["multiply_by"],
                            "vehicle_type": vehicle_type,
                            "valid_time": valid_time,
                            "run": run,
                        },
                    }
                )
    return {"type": "FeatureCollection", "features": features}


def _parse_geojson(text: str) -> dict[str, Any]:
    import json

    return json.loads(text)


def build_custom_model(areas_fc: dict[str, Any]) -> dict[str, Any]:
    """Turns derive_areas() output into a GraphHopper custom_model. Uses an
    if/else_if chain (never independent `if` rules) ordered deepest-band
    first, so an edge inside two overlapping buffers from different bands
    only ever takes the deepest (first-matching) penalty instead of having
    both multiply together."""
    priority: list[dict[str, str]] = []
    for index, feature in enumerate(areas_fc["features"]):
        clause = "if" if index == 0 else "else_if"
        priority.append(
            {
                clause: f"in_{feature['id']}",
                "multiply_by": str(feature["properties"]["multiply_by"]),
            }
        )
    return {"priority": priority, "areas": areas_fc}
