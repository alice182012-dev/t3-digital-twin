"""Loads one run's per-edge depth series from edge_depth, runs metrics.extract on each,
and writes one flood_segment_metrics row per wet edge per vehicle type.

Usage: python extract_run.py RUN_TS   (RUN_TS as the DAG names it, for example 20260923T100000)

Create the output table first with scripts/database/create_flood_metrics_tables.py.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import psycopg2
from psycopg2.extras import execute_values

from metrics import Closed, DepthSeries, NeverImpassable, Passability, SegmentMetrics, extract

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
FLOOD_UTILS_DIR = SCRIPTS_DIR.parent / "floodmap" / "graphhopper-flood-road" / "scripts"

# edge_depth holds the wet edges only, so a dry step of a wet edge has no row. edge_depth_run.valid_times lists every
# step of the run, and extract fills the missing ones with 0, as the old per-piece rows did for a wet piece. The edge
# depth tables hold UTC, and flood_history and the metrics already written hold local time.
VIETNAM_UTC_OFFSET = timedelta(hours=7)

STEPS_SQL = "SELECT valid_times FROM edge_depth_run WHERE run_ts = %(run)s"

LOAD_SQL = """
SELECT d.edge_key, ST_AsEWKB(e.geom), d.valid_time_utc, d.depth_cm
FROM edge_depth d
LEFT JOIN graph_edge e USING (edge_key)
WHERE d.run_ts = %(run)s
ORDER BY d.edge_key, d.valid_time_utc
"""

INSERT_SQL = """
INSERT INTO flood_segment_metrics (
    run_ts, edge_key, vehicle_type, impassable_from_m,
    window_start, window_end,
    peak_time, peak_depth_m, time_to_peak, peak_at_window_end, recession_onset,
    forecast_depth_1h_m, forecast_depth_2h_m,
    passability, closed_at, pre_closure_time, restored_at,
    geom_4326
)
VALUES %s
"""

INSERT_TEMPLATE = """(
    %(run_ts)s, %(edge_key)s, %(vehicle_type)s, %(impassable_from_m)s,
    %(window_start)s, %(window_end)s,
    %(peak_time)s, %(peak_depth_m)s, %(time_to_peak)s, %(peak_at_window_end)s,
    %(recession_onset)s,
    %(forecast_depth_1h_m)s, %(forecast_depth_2h_m)s,
    %(passability)s, %(closed_at)s, %(pre_closure_time)s, %(restored_at)s,
    ST_GeomFromEWKB(%(geom_ewkb)s)
)"""


@dataclass(frozen=True)
class Segment:
    edge_key: str
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


def segments_from_rows(rows: Iterable[tuple], steps: Sequence[datetime]) -> list[Segment]:
    """rows are LOAD_SQL's (edge_key, geom_ewkb, valid_time_utc, depth_cm), ordered by edge_key then time. steps are
    the run's valid times, in UTC. Each edge gets one depth per step, 0 where the edge is dry, and local times."""
    steps = sorted(steps)
    segments = []
    for edge_key, group in groupby(rows, key=lambda row: row[0]):
        group = list(group)
        if group[0][1] is None:
            raise ValueError(f"edge {edge_key} is not in graph_edge, so it has no geometry")
        wet = {row[2]: row[3] for row in group}
        unknown = sorted(set(wet) - set(steps))
        if unknown:
            raise ValueError(f"edge {edge_key} has a depth at {unknown[0]}, which is not a step of the run")
        segments.append(
            Segment(
                edge_key=edge_key,
                geom_ewkb=bytes(group[0][1]),
                series=DepthSeries(
                    times=tuple(step + VIETNAM_UTC_OFFSET for step in steps),
                    depths_m=tuple(wet.get(step, 0) / 100 for step in steps),
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
        "edge_key": segment.edge_key,
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
    """The wet edges of a run. A run with no wet edge gives none, and a run the registry does not know is an error."""
    with conn.cursor() as cur:
        cur.execute(STEPS_SQL, {"run": run_ts})
        registry = cur.fetchone()
        if registry is None:
            raise ValueError(f"no edge_depth_run row for run {run_ts}")
        cur.execute(LOAD_SQL, {"run": run_ts})
        return segments_from_rows(cur.fetchall(), registry[0])


def write_run(conn, run_ts: str, rows: list[dict]) -> None:
    """Replaces the run's edge-keyed rows in one transaction, so a rerun converges on the latest extraction even when
    the run's edge set changed. Rows keyed by segment_key, from the piece-based extraction, are kept."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM flood_segment_metrics WHERE run_ts = %s AND edge_key IS NOT NULL", (run_ts,))
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
