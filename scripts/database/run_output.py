"""The run manifest `flood_run_output`: one row per run and published output (US-108).

A consumer outside Airflow reads this table to learn which outputs of a run are ready, instead of
polling flood_depth_raster_tile, flood_extent_polygon, and the edge depth `latest` file. Each writer
calls `record` as its last write, so a row never names an output that is not there.
"""

from __future__ import annotations

from collections.abc import Collection
from enum import Enum


class Output(str, Enum):
    DEPTH_RASTER = "depth_raster"
    EXTENT = "extent"
    EDGE_DEPTH = "edge_depth"


_RECORD_SQL = """
INSERT INTO flood_run_output (run_ts, output) VALUES (%(run_ts)s, %(output)s)
ON CONFLICT (run_ts, output) DO UPDATE SET published_at = NOW()
"""

_PRUNE_SQL = """
DELETE FROM flood_run_output
WHERE run_ts <> ALL(%(always_keep)s)
  AND run_ts NOT IN (
      SELECT DISTINCT run_ts FROM flood_run_output ORDER BY run_ts DESC LIMIT %(keep_runs)s
  )
"""


def record(cur, run_ts: str, output: Output) -> None:
    """Marks `output` of `run_ts` as published. A rerun keeps one row and refreshes its published_at."""
    cur.execute(_RECORD_SQL, {"run_ts": run_ts, "output": output.value})


def prune(cur, keep_runs: int, always_keep: Collection[str]) -> None:
    """Deletes the rows of every run outside the newest `keep_runs` by run_ts, never a run of `always_keep`.
    run_ts is a fixed-width YYYYMMDDTHHMMSS string, so its text order is its time order."""
    cur.execute(_PRUNE_SQL, {"keep_runs": keep_runs, "always_keep": sorted(always_keep)})
