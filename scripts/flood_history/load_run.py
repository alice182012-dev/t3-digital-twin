"""Copies one run's per-edge flood depth from edge_depth into depth_history in TimescaleDB, and the run's moments
into history_moment (US-106, US-122, D-032, D-036, D-038). The moments come from edge_depth_run.valid_times.

Usage: python load_run.py RUN_TS   (RUN_TS as the DAG names it, for example 20260924T164803)

When two runs cover the same moment, the run with the later issued_at wins every piece of that moment: a loser's
rows for the moment are replaced, so an edge only the loser wet has no row and reads as dry. Loading a run again
replaces its own rows. The table rules are in artifacts/docs/concepts/timescaledb-schema.md.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import psycopg2
from psycopg2.extras import execute_values

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "database"))
sys.path.insert(0, str(SCRIPTS_DIR / "flood_roads"))
from flood_on_roads import VIETNAM_UTC_OFFSET, run_timestamp  # noqa: E402

CYCLE = "constant_cycle"


class DepthRow(NamedTuple):
    edge_key: str
    valid_time: datetime
    depth_m: float


@dataclass(frozen=True)
class RunSlice:
    """One run as depth_history sees it. Every datetime is timezone-aware UTC."""

    run_ts: str
    issued_at: datetime
    moments: tuple[datetime, ...]
    rows: tuple[DepthRow, ...]


@dataclass(frozen=True)
class LoadResult:
    run_ts: str
    written: tuple[datetime, ...]
    skipped: tuple[datetime, ...]
    rows: tuple[DepthRow, ...]

    def describe(self) -> str:
        return (
            f"Run {self.run_ts}: {len(self.written)} moments written, {len(self.skipped)} skipped for a later run, "
            f"{len(self.rows)} rows."
        )


class LoadRunError(ValueError):
    pass


def vietnam_to_utc(local: datetime) -> datetime:
    """A naive Vietnam local time, as the run name keeps it, as an aware UTC time."""
    return (local - VIETNAM_UTC_OFFSET).replace(tzinfo=timezone.utc)


def build_slice(run_ts: str, valid_times: list[datetime], wet_rows: list[tuple[str, datetime, int]]) -> RunSlice:
    """`valid_times` are the run's times in edge_depth_run, and `wet_rows` are the run's (edge_key, valid_time, depth_cm)
    rows of edge_depth. Both are naive UTC. Only wet edges have a row, and the others read as dry."""
    if not valid_times:
        raise LoadRunError(f"no valid times in edge_depth_run for run {run_ts}, so it covers no moment")
    moments = tuple(sorted(t.replace(tzinfo=timezone.utc) for t in set(valid_times)))
    rows = tuple(DepthRow(edge_key, t.replace(tzinfo=timezone.utc), depth_cm / 100) for edge_key, t, depth_cm in wet_rows)
    stray = sorted({row.valid_time for row in rows} - set(moments))
    if stray:
        raise LoadRunError(f"run {run_ts} has edge_depth rows at {stray}, which its valid times do not cover")
    return RunSlice(run_ts=run_ts, issued_at=vietnam_to_utc(run_timestamp(run_ts)), moments=moments, rows=rows)


def plan_write(run: RunSlice, held: dict[datetime, datetime]) -> LoadResult:
    """`held` maps each moment already in history_moment to its issued_at. A moment held by a later run is
    skipped; a moment held by an earlier run, or by this run, is written."""
    skipped = tuple(m for m in run.moments if m in held and held[m] > run.issued_at)
    written = tuple(m for m in run.moments if m not in skipped)
    written_set = set(written)
    rows = tuple(row for row in run.rows if row.valid_time in written_set)
    return LoadResult(run_ts=run.run_ts, written=written, skipped=skipped, rows=rows)


def read_run(conn, run_ts: str) -> RunSlice:
    """Reads one run from storage-postgres. The run's moments are its valid times in edge_depth_run, which a run with
    no wet edge still has. A run the registry does not list is an error."""
    with conn, conn.cursor() as cur:
        cur.execute("SELECT valid_times FROM edge_depth_run WHERE run_ts = %s", (run_ts,))
        registry = cur.fetchone()
        if registry is None:
            raise LoadRunError(f"no edge_depth_run row for run {run_ts}")
        cur.execute("SELECT edge_key, valid_time_utc, depth_cm FROM edge_depth WHERE run_ts = %s", (run_ts,))
        wet_rows = cur.fetchall()
    return build_slice(run_ts, registry[0], wet_rows)


def write_run(conn, run: RunSlice) -> LoadResult:
    """Writes one run to TimescaleDB in one transaction. The lock is table-wide, not per run: two runs that
    share a moment would otherwise both read history_moment before either writes, and the earlier run could win."""
    with conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('depth_history'))")
        cur.execute(
            "SELECT valid_time, issued_at FROM history_moment WHERE valid_time = ANY(%s)", (list(run.moments),)
        )
        result = plan_write(run, dict(cur.fetchall()))
        if not result.written:
            return result
        cur.execute("DELETE FROM depth_history WHERE valid_time = ANY(%s)", (list(result.written),))
        execute_values(
            cur,
            "INSERT INTO depth_history (edge_key, valid_time, depth_m, cycle, issued_at) VALUES %s",
            [(*row, CYCLE, run.issued_at) for row in result.rows],
            page_size=1000,
        )
        execute_values(
            cur,
            "INSERT INTO history_moment (valid_time, issued_at) VALUES %s "
            "ON CONFLICT (valid_time) DO UPDATE SET issued_at = EXCLUDED.issued_at, created_at = EXCLUDED.created_at",
            [(moment, run.issued_at) for moment in result.written],
        )
    return result


def load(run_ts: str) -> LoadResult:
    from db_config import DB_CONFIG, TIMESCALE_DB_CONFIG

    source = psycopg2.connect(**DB_CONFIG)
    try:
        run = read_run(source, run_ts)
    finally:
        source.close()
    target = psycopg2.connect(**TIMESCALE_DB_CONFIG)
    try:
        return write_run(target, run)
    finally:
        target.close()


def main(argv: list[str] | None = None) -> LoadResult:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_ts")
    args = parser.parse_args(argv)

    result = load(args.run_ts)
    print(result.describe())
    return result


if __name__ == "__main__":
    main()
