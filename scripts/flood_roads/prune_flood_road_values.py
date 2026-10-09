"""Deletes the runs of flood_road_values older than a window before its newest run, and their
flood_road_file rows (US-086, decision D-017).

Usage: python prune_flood_road_values.py [--keep-hours N] [--dry-run] [--target TABLE]

The window is measured from the newest run in the table, not from the clock, so a paused DAG or a
replay with past timestamps never empties it. A run exactly at the cutoff is kept.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2 import sql

import flood_on_roads

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_KEEP_HOURS = 24


@dataclass(frozen=True)
class PruneResult:
    cutoff: datetime | None
    newest_run: datetime | None
    runs_deleted: int
    rows_deleted: int
    runs_kept: int


_RUNS_SQL = "SELECT timestamp, count(*) FROM {target} GROUP BY timestamp ORDER BY timestamp"

_DELETE_VALUES_SQL = "DELETE FROM {target} WHERE timestamp = %s"

_DELETE_FILES_SQL = "DELETE FROM flood_road_file WHERE timestamp = %s"


def prune(
    conn, keep_hours: int, target_table: str = flood_on_roads.DEFAULT_TARGET, dry_run: bool = False
) -> PruneResult:
    """One transaction per run, so no transaction holds millions of row deletes and a failure
    leaves the earlier runs deleted and the later ones intact."""
    target = sql.Identifier(target_table)
    with conn, conn.cursor() as cur:
        cur.execute(sql.SQL(_RUNS_SQL).format(target=target))
        rows_by_run = dict(cur.fetchall())
    if not rows_by_run:
        return PruneResult(cutoff=None, newest_run=None, runs_deleted=0, rows_deleted=0, runs_kept=0)

    newest = max(rows_by_run)
    cutoff = newest - timedelta(hours=keep_hours)
    old_runs = sorted(run for run in rows_by_run if run < cutoff)

    rows_deleted = 0
    for run in old_runs:
        if dry_run:
            rows_deleted += rows_by_run[run]
            continue
        with conn, conn.cursor() as cur:
            flood_on_roads.lock_run(cur, target_table, run)
            cur.execute(sql.SQL(_DELETE_VALUES_SQL).format(target=target), (run,))
            rows_deleted += cur.rowcount
            # flood_road_file rows belong to flood_road_values. A shadow table has no foreign key to
            # them, and deleting them would cascade into the real table. Values go first so their
            # delete uses the timestamp index; flood_road_values.file_id has none.
            if target_table == flood_on_roads.DEFAULT_TARGET:
                cur.execute(_DELETE_FILES_SQL, (run,))

    return PruneResult(
        cutoff=cutoff,
        newest_run=newest,
        runs_deleted=len(old_runs),
        rows_deleted=rows_deleted,
        runs_kept=len(rows_by_run) - len(old_runs),
    )


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {text!r}")
    return value


def main(argv: list[str] | None = None) -> PruneResult:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep-hours", type=positive_int, default=DEFAULT_KEEP_HOURS)
    parser.add_argument("--dry-run", action="store_true", help="count what would be deleted, delete nothing")
    parser.add_argument("--target", default=flood_on_roads.DEFAULT_TARGET)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(SCRIPTS_DIR / "database"))
    from db_config import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        result = prune(conn, args.keep_hours, target_table=args.target, dry_run=args.dry_run)
    finally:
        conn.close()

    verb = "Would delete" if args.dry_run else "Deleted"
    print(
        f"{verb} {result.runs_deleted} runs ({result.rows_deleted} rows) of {args.target} older than "
        f"{result.cutoff}, {args.keep_hours} h before the newest run {result.newest_run}; "
        f"{result.runs_kept} runs kept."
    )
    return result


if __name__ == "__main__":
    main()
