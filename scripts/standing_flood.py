"""Tells whether the flood of earlier runs still stands on the roads, so the rain gate does not end a storm.

The gate in flood_mapping_dag.py reads forecast rain. A flood outlasts the rain, so the gate applies only from a
dry state. Once the simulation is on, it runs every slot until two things hold together: the edge depth table has
stayed under DRY_DEPTH_M for DRY_RUNS_TO_STOP runs in a row, and the forecast rain is 0.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

DRY_RUNS_TO_STOP = 5
# A run whose deepest edge is under 5 cm is a dry run. edge_depth.depth_cm is whole centimetres, rounded to the nearest.
DRY_DEPTH_M = 0.05
# Runs are one 15-minute slot apart. A bigger gap means the chain broke, and older dry runs are not part of this one.
MAX_RUN_GAP = timedelta(minutes=30)
# The newest run is written about 12 minutes after its slot starts. Older than this, no run is in progress.
MAX_NEWEST_AGE = timedelta(minutes=45)


@dataclass(frozen=True)
class RunDepth:
    """One run of the edge depth table: when it starts, its deepest edge over all steps in metres, and its age."""

    timestamp: datetime
    max_depth: float
    age: timedelta


def assess(runs_newest_first: Sequence[RunDepth], max_rain_mm_hr: float, dry_depth_m: float = DRY_DEPTH_M) -> dict:
    """Decide from the newest runs and the forecast whether a simulation that is on stays on.

    Off when no run is in progress (a dry state, where the forecast gate decides), or when the newest
    DRY_RUNS_TO_STOP runs are all dry and no rain is forecast. On otherwise."""
    if not runs_newest_first:
        return _result(False, "no_run", 0, None)
    newest_age = runs_newest_first[0].age
    if newest_age > MAX_NEWEST_AGE:
        return _result(False, "chain_ended", 0, newest_age)

    dry_runs = 0
    previous = None
    for run in runs_newest_first:
        if run.max_depth >= dry_depth_m:
            break
        if previous is not None and previous.timestamp - run.timestamp > MAX_RUN_GAP:
            break
        dry_runs += 1
        previous = run
    if dry_runs >= DRY_RUNS_TO_STOP and max_rain_mm_hr <= 0:
        return _result(False, "dry_and_no_rain", dry_runs, newest_age)
    reason = "rain_forecast" if dry_runs >= DRY_RUNS_TO_STOP else "standing_flood"
    return _result(True, reason, dry_runs, newest_age)


def _result(stands: bool, reason: str, dry_runs: int, newest_age) -> dict:
    return {
        "stands": stands,
        "reason": reason,
        "dry_runs_in_a_row": dry_runs,
        "dry_runs_to_stop": DRY_RUNS_TO_STOP,
        "newest_run_age_min": None if newest_age is None else round(newest_age.total_seconds() / 60, 1),
    }


_TABLE_SQL = "SELECT to_regclass('edge_depth_run') IS NOT NULL"

# 9c registers one edge_depth_run row per run and writes edge_depth rows only for edges that were wet at some step, so
# a run with no rows is a dry run at 0. built_at is the database clock, as is LOCALTIMESTAMP, so the age does not depend
# on the replay clock.
_RUNS_SQL = """
SELECT to_timestamp(r.run_ts, 'YYYYMMDD"T"HH24MISS')::timestamp,
       coalesce(max(d.depth_cm), 0) / 100.0,
       LOCALTIMESTAMP - r.built_at
FROM edge_depth_run r
LEFT JOIN edge_depth d ON d.run_ts = r.run_ts
GROUP BY r.run_ts, r.built_at
ORDER BY r.run_ts DESC
LIMIT %(limit)s
"""


def read_standing_flood(conn, max_rain_mm_hr: float, dry_depth_m: float = DRY_DEPTH_M) -> dict:
    """Read the newest runs of the edge depth table over `conn` and assess them with the forecast. A database that has
    no edge_depth_run table has had no run, which is a dry state."""
    with conn.cursor() as cur:
        cur.execute(_TABLE_SQL)
        if not cur.fetchone()[0]:
            return assess([], max_rain_mm_hr, dry_depth_m)
        cur.execute(_RUNS_SQL, {"limit": DRY_RUNS_TO_STOP})
        runs = [RunDepth(timestamp, float(depth), age) for timestamp, depth, age in cur.fetchall()]
    return assess(runs, max_rain_mm_hr, dry_depth_m)
