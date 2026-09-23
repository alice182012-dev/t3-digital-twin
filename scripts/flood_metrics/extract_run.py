"""Loads one run's per-segment depth series from flood_road_values, runs metrics.extract on each,
and writes one flood_segment_metrics row per segment per vehicle type.

Usage: python extract_run.py RUN_TS   (RUN_TS as the DAG names it, for example 20260923T100000)

Create the output table first with scripts/database/create_flood_metrics_tables.py.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import Iterable, Mapping

import psycopg2
from psycopg2.extras import execute_values

from metrics import Closed, DepthSeries, NeverImpassable, Passability, SegmentMetrics, extract

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
FLOOD_UTILS_DIR = SCRIPTS_DIR.parent / "floodmap" / "graphhopper-flood-road" / "scripts"

# build_rows (scripts/database/geojson_to_pg.py) writes one row per (feature, timeseries item),
# repeating the feature's road_name and geometry, so equal geometry identifies one segment.
LOAD_SQL = """
SELECT md5(ST_AsEWKB(geom_4326)) AS segment_key,
       road_name,
       ST_AsEWKB(geom_4326),
       forecast_time,
       depth
FROM flood_road_values
WHERE timestamp = %(run)s
ORDER BY segment_key, forecast_time
"""

INSERT_SQL = """
INSERT INTO flood_segment_metrics (
    run_ts, segment_key, road_name, vehicle_type, impassable_from_m,
    window_start, window_end,
    peak_time, peak_depth_m, time_to_peak, peak_at_window_end, recession_onset,
    forecast_depth_1h_m, forecast_depth_2h_m,
    passability, closed_at, pre_closure_time, restored_at,
    geom_4326
)
VALUES %s
"""

INSERT_TEMPLATE = """(
    %(run_ts)s, %(segment_key)s, %(road_name)s, %(vehicle_type)s, %(impassable_from_m)s,
    %(window_start)s, %(window_end)s,
    %(peak_time)s, %(peak_depth_m)s, %(time_to_peak)s, %(peak_at_window_end)s,
    %(recession_onset)s,
    %(forecast_depth_1h_m)s, %(forecast_depth_2h_m)s,
    %(passability)s, %(closed_at)s, %(pre_closure_time)s, %(restored_at)s,
    ST_GeomFromEWKB(%(geom_ewkb)s)
)"""


@dataclass(frozen=True)
class Segment:
    segment_key: str
    road_name: str | None
    geom_ewkb: bytes
    series: DepthSeries


def impassable_from_m() -> dict[str, float]:
    """The deepest DEPTH_BANDS band (band_max None) is the one flood_areas.py makes impassable
    with `depth >= band_min`. Reading it from flood_utils keeps metrics and routing on one set of
    thresholds instead of a copy that can drift."""
    if str(FLOOD_UTILS_DIR) not in sys.path:
        sys.path.insert(0, str(FLOOD_UTILS_DIR))
    import flood_utils

    return {
        vehicle: next(b["band_min"] for b in flood_utils.depth_bands_m(vehicle) if b["band_max"] is None)
        for vehicle in flood_utils.vehicle_types()
    }


def run_timestamp(run_ts: str) -> datetime:
    """Same format geojson_to_pg.parse_timestamp reads the run folder with."""
    return datetime.strptime(run_ts, "%Y%m%dT%H%M%S")


def segments_from_rows(rows: Iterable[tuple]) -> list[Segment]:
    """rows are LOAD_SQL's (segment_key, road_name, geom_ewkb, forecast_time, depth), ordered by
    segment_key then forecast_time."""
    segments = []
    for segment_key, group in groupby(rows, key=lambda row: row[0]):
        group = list(group)
        road_names = {row[1] for row in group}
        if len(road_names) != 1:
            raise ValueError(f"segment {segment_key} has several road names: {sorted(map(str, road_names))}")
        if any(row[4] is None for row in group):
            raise ValueError(f"segment {segment_key} has a NULL depth")
        segments.append(
            Segment(
                segment_key=segment_key,
                road_name=group[0][1],
                geom_ewkb=bytes(group[0][2]),
                series=DepthSeries(
                    times=tuple(row[3] for row in group),
                    depths_m=tuple(float(row[4]) for row in group),
                ),
            )
        )
    return segments


def metric_rows(
    run_ts: str,
    segment: Segment,
    metrics: SegmentMetrics,
    thresholds_m: Mapping[str, float],
) -> list[dict]:
    peak = metrics.peak
    shared = {
        "run_ts": run_ts,
        "segment_key": segment.segment_key,
        "road_name": segment.road_name,
        "window_start": metrics.window_start,
        "window_end": metrics.window_end,
        "peak_time": None if peak is None else peak.at,
        "peak_depth_m": None if peak is None else peak.depth_m,
        "time_to_peak": metrics.time_to_peak,
        "peak_at_window_end": None if peak is None else peak.at_window_end,
        "recession_onset": metrics.recession_onset,
        "forecast_depth_1h_m": metrics.forecast_depth_1h_m,
        "forecast_depth_2h_m": metrics.forecast_depth_2h_m,
        "geom_ewkb": segment.geom_ewkb,
    }
    return [
        {
            **shared,
            "vehicle_type": vehicle,
            "impassable_from_m": thresholds_m[vehicle],
            **_passability_columns(passability),
        }
        for vehicle, passability in metrics.passability.items()
    ]


def _passability_columns(passability: Passability) -> dict:
    match passability:
        case NeverImpassable():
            return {"passability": "never_impassable", "closed_at": None, "pre_closure_time": None, "restored_at": None}
        case Closed(closed_at=closed_at, pre_closure_at=pre_closure_at, restored_at=restored_at):
            return {
                "passability": "not_restored" if restored_at is None else "restored",
                "closed_at": closed_at,
                "pre_closure_time": pre_closure_at,
                "restored_at": restored_at,
            }


def load_segments(conn, run_ts: str) -> list[Segment]:
    with conn.cursor() as cur:
        cur.execute(LOAD_SQL, {"run": run_timestamp(run_ts)})
        return segments_from_rows(cur.fetchall())


def write_run(conn, run_ts: str, rows: list[dict]) -> None:
    """Replaces the run's rows in one transaction, so a rerun converges on the latest extraction
    even when the run's segment set changed (geojson_to_pg's delete_old_values does the same)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM flood_segment_metrics WHERE run_ts = %s", (run_ts,))
        execute_values(
            cur,
            INSERT_SQL,
            [{**row, "geom_ewkb": psycopg2.Binary(row["geom_ewkb"])} for row in rows],
            template=INSERT_TEMPLATE,
            page_size=1000,
        )
    conn.commit()


def extract_run(conn, run_ts: str) -> int:
    segments = load_segments(conn, run_ts)
    if not segments:
        raise ValueError(f"no flood_road_values rows for run {run_ts}")
    thresholds_m = impassable_from_m()
    rows = [
        row
        for segment in segments
        for row in metric_rows(run_ts, segment, extract(segment.series, thresholds_m), thresholds_m)
    ]
    write_run(conn, run_ts, rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_ts")
    args = parser.parse_args()

    sys.path.insert(0, str(SCRIPTS_DIR / "database"))
    from db_config import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        written = extract_run(conn, args.run_ts)
    finally:
        conn.close()
    print(f"Wrote {written} flood_segment_metrics rows for run {args.run_ts}")


if __name__ == "__main__":
    main()
