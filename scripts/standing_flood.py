"""Tells whether the flood of earlier runs is still changing on the roads, so the rain gate does not end a storm.

The gate in flood_mapping_dag.py reads forecast rain. A flood outlasts the rain, so the gate applies only from a dry
state. Once the simulation is on, it runs every slot until two things hold together: the edge depth table has stopped
changing for STEADY_RUNS_TO_STOP runs in a row, and the forecast rain is 0. The model holds permanent water that never
drains (BL-030), so the test is that depths stop moving and not that they fall under a limit.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

STEADY_RUNS_TO_STOP = 5
# Two runs are steady when no edge differs by more than this many centimetres. edge_depth.depth_cm is whole centimetres,
# rounded to the nearest, so a 1 cm move is rounding noise and 2 cm is a real change.
STEADY_CHANGE_CM = 1.0
# Runs are one 15-minute slot apart. A bigger gap means the chain broke, and older runs are not part of this one.
MAX_RUN_GAP = timedelta(minutes=30)
# The newest run is written about 12 minutes after its slot starts. Older than this, no run is in progress.
MAX_NEWEST_AGE = timedelta(minutes=45)


@dataclass(frozen=True)
class RunDepth:
    """One run of the edge depth table: when it starts, the deepest depth of each wet edge over all steps in
    centimetres, and its age. An edge with no entry was dry at every step, which is a depth of 0."""

    timestamp: datetime
    depths_cm: Mapping[str, float]
    age: timedelta


def _is_steady(newer: RunDepth, older: RunDepth) -> bool:
    edges = newer.depths_cm.keys() | older.depths_cm.keys()
    return all(abs(newer.depths_cm.get(edge, 0) - older.depths_cm.get(edge, 0)) <= STEADY_CHANGE_CM for edge in edges)


def assess(runs_newest_first: Sequence[RunDepth], max_rain_mm_hr: float) -> dict:
    """Decide from the newest runs and the forecast whether a simulation that is on stays on.

    Off when no run is in progress (a dry state, where the forecast gate decides), or when the newest
    STEADY_RUNS_TO_STOP runs have no edge that changed by more than STEADY_CHANGE_CM between consecutive runs and no
    rain is forecast. On otherwise, so a chain with fewer runs than that keeps running."""
    if not runs_newest_first:
        return _result(False, "no_run", 0, None)
    newest_age = runs_newest_first[0].age
    if newest_age > MAX_NEWEST_AGE:
        return _result(False, "chain_ended", 0, newest_age)

    steady_runs = 1
    for newer, older in zip(runs_newest_first, runs_newest_first[1:]):
        if newer.timestamp - older.timestamp > MAX_RUN_GAP or not _is_steady(newer, older):
            break
        steady_runs += 1
    if steady_runs >= STEADY_RUNS_TO_STOP and max_rain_mm_hr <= 0:
        return _result(False, "steady_and_no_rain", steady_runs, newest_age)
    reason = "rain_forecast" if steady_runs >= STEADY_RUNS_TO_STOP else "depths_changing"
    return _result(True, reason, steady_runs, newest_age)


def _result(stands: bool, reason: str, steady_runs: int, newest_age) -> dict:
    return {
        "stands": stands,
        "reason": reason,
        "steady_runs_in_a_row": steady_runs,
        "steady_runs_to_stop": STEADY_RUNS_TO_STOP,
        "newest_run_age_min": None if newest_age is None else round(newest_age.total_seconds() / 60, 1),
    }


_TABLE_SQL = "SELECT to_regclass('edge_depth_run') IS NOT NULL"

# 9c registers one edge_depth_run row per run and writes edge_depth rows only for edges that were wet at some step, so
# a run with no rows has no wet edge (edge_key NULL here). built_at is the database clock, as is LOCALTIMESTAMP, so the
# age does not depend on the replay clock.
_RUNS_SQL = """
WITH newest AS (
    SELECT run_ts, built_at FROM edge_depth_run ORDER BY run_ts DESC LIMIT %(limit)s
)
SELECT to_timestamp(r.run_ts, 'YYYYMMDD"T"HH24MISS')::timestamp,
       LOCALTIMESTAMP - r.built_at,
       d.edge_key,
       max(d.depth_cm)
FROM newest r
LEFT JOIN edge_depth d ON d.run_ts = r.run_ts
GROUP BY r.run_ts, r.built_at, d.edge_key
ORDER BY r.run_ts DESC
"""


def read_standing_flood(conn, max_rain_mm_hr: float) -> dict:
    """Read the newest runs of the edge depth table over `conn` and assess them with the forecast. A database that has
    no edge_depth_run table has had no run, which is a dry state."""
    with conn.cursor() as cur:
        cur.execute(_TABLE_SQL)
        if not cur.fetchone()[0]:
            return assess([], max_rain_mm_hr)
        cur.execute(_RUNS_SQL, {"limit": STEADY_RUNS_TO_STOP})
        rows = cur.fetchall()
    runs = {}
    for timestamp, age, edge_key, depth_cm in rows:
        run = runs.setdefault(timestamp, RunDepth(timestamp, {}, age))
        if edge_key is not None:
            run.depths_cm[edge_key] = depth_cm
    return assess(list(runs.values()), max_rain_mm_hr)
