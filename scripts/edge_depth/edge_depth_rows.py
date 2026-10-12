"""Writes a run's wet edges to `edge_depth` and the run to its registry `edge_depth_run` (US-118, D-038).

`build_edge_depth.py` samples every edge at every step for the binary table of the engine. The same pass hands
its wet edges to write_run, so one sampler serves the engine and every reader of the database. The registry row
holds the run's forecast times, so a run with no wet edge still covers its times. See
scripts/database/create_edge_depth_tables.py for the tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, NamedTuple, Sequence

from psycopg2.extras import execute_values

DEFAULT_KEEP_HOURS = 24
_RUN_TS_FORMAT = "%Y%m%dT%H%M%S"
_PAGE_SIZE = 5000


class WetEdge(NamedTuple):
    valid_time_utc: datetime
    edge_key: str
    depth_cm: int


@dataclass(frozen=True)
class WriteResult:
    rows: int
    runs_pruned: int


def run_time(run_ts: str) -> datetime:
    """The time in a run name such as 20260924T164803. Raises ValueError for another shape."""
    return datetime.strptime(run_ts, _RUN_TS_FORMAT)


def check_keep_hours(keep_hours: int) -> None:
    if keep_hours < 1:
        raise ValueError(f"keep_hours must be at least 1, got {keep_hours}")


_RUN_SQL = """
INSERT INTO edge_depth_run (run_ts, graph_hash, valid_times) VALUES (%(run_ts)s, %(graph_hash)s, %(valid_times)s)
"""

_ROWS_SQL = "INSERT INTO edge_depth (run_ts, valid_time_utc, edge_key, depth_cm) VALUES %s"

_NEWEST_SQL = "SELECT max(run_ts) FROM edge_depth_run"

_PRUNE_SQL = "DELETE FROM edge_depth_run WHERE run_ts < %(cutoff)s AND run_ts <> %(run_ts)s"


def write_run(
    conn,
    run_ts: str,
    graph_hash: str,
    valid_times: Sequence[datetime],
    wet: Iterable[WetEdge],
    keep_hours: int = DEFAULT_KEEP_HOURS,
) -> WriteResult:
    """Replaces the run's registry row and rows in one transaction, then deletes the runs that are older than
    `keep_hours` before the newest run. The window is measured from the newest run in the table, not from the
    clock, so a paused DAG or a replay never empties it. A run exactly at the cutoff stays, and so does the run
    just written.

    A rebuild of one run replaces it, so the row count does not change. A failure leaves the earlier state."""
    check_keep_hours(keep_hours)
    run_time(run_ts)
    rows = list(wet)
    known = set(valid_times)
    stray = sorted({row.valid_time_utc for row in rows} - known)
    if stray:
        raise ValueError(f"rows for {stray[0]} are outside the forecast times of run {run_ts}")
    with conn, conn.cursor() as cur:
        # Two builds of one run must not both pass the delete and then both insert.
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('edge_depth:' || %s))", (run_ts,))
        cur.execute("DELETE FROM edge_depth_run WHERE run_ts = %s", (run_ts,))
        cur.execute(_RUN_SQL, {"run_ts": run_ts, "graph_hash": graph_hash, "valid_times": sorted(known)})
        if rows:
            execute_values(
                cur, _ROWS_SQL, [(run_ts, *row) for row in rows], page_size=_PAGE_SIZE
            )
        cur.execute(_NEWEST_SQL)
        newest = run_time(cur.fetchone()[0])
        cutoff = (newest - timedelta(hours=keep_hours)).strftime(_RUN_TS_FORMAT)
        cur.execute(_PRUNE_SQL, {"cutoff": cutoff, "run_ts": run_ts})
        pruned = cur.rowcount
    return WriteResult(rows=len(rows), runs_pruned=pruned)
