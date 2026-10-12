"""Publishes an edge depth table: points `latest` at it in one step and keeps the newest few (US-042).

build_edge_depth.py writes <run_ts>.bin into the table folder. This module then:

1. reads the file back whole, so a table that does not read (truncated, wrong version, a header that names
   another run) is removed and never pointed at;
2. moves `latest` to it, atomically (edge_depth_table.write_latest), but only forward: two runs can overlap,
   and the older one can finish last, and its table must not take the pointer back;
3. keeps the newest `keep` tables, plus the one `latest` names, and removes the rest;
4. removes temporary files that a killed build or publish left, once they are an hour old.

A failure before step 2 leaves `latest` on the previous table. Readers see the old table or the new one.
The tables live on a Docker volume that the Airflow worker writes and the readers mount read-only
(artifacts/archive/plans/edge-depth-table-publish.md, decision 1).
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Collection
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import edge_depth_table
from edge_depth_table import TableFormatError

try:
    import fcntl
except ImportError:  # not POSIX; the worker is Linux, this keeps the module importable elsewhere
    fcntl = None

DEFAULT_KEEP = 3
STALE_TEMPORARY_SECONDS = 3600

# The DAG names a run YYYYMMDDTHHMMSS, so the names sort in time order.
_TABLE_NAME = re.compile(r"^(\d{8}T\d{6})\.bin$")


class PublishError(ValueError):
    pass


@dataclass(frozen=True)
class PublishResult:
    latest: str
    previous: str | None
    moved: bool
    removed: tuple[str, ...]
    kept: tuple[str, ...]


def publish_table(
    table_dir, table_name: str, keep: int = DEFAULT_KEEP, now: float | None = None, also_keep: Collection[str] = ()
) -> PublishResult:
    """Publishes table_name, which is already in table_dir. The tables named in `also_keep`, such as the pinned run's,
    stay whatever their age. Raises ValueError for keep < 1 and PublishError
    for a name that is not a run table, a missing file, or a file that does not read."""
    if keep < 1:
        raise ValueError(f"keep must be at least 1: {keep}")
    table_dir = Path(table_dir)
    match = _TABLE_NAME.match(table_name)
    if not match:
        raise PublishError(f"{table_name!r} is not a table name (expected YYYYMMDDTHHMMSS.bin)")
    path = table_dir / table_name
    if not path.is_file():
        raise PublishError(f"{path} does not exist")
    try:
        table = edge_depth_table.read_table(path)
    except TableFormatError as e:
        path.unlink(missing_ok=True)
        raise PublishError(f"{table_name} is not a valid table, so it is removed and `latest` stays: {e}") from e
    if table.header.run_name != match.group(1):
        path.unlink(missing_ok=True)
        raise PublishError(
            f"{table_name} holds run {table.header.run_name}, not {match.group(1)}, so it is removed and `latest` stays"
        )

    with _locked(table_dir):
        previous = _current(table_dir)
        moved = previous is None or table_name > previous
        if moved:
            edge_depth_table.write_latest(table_dir, table_name)
        latest = table_name if moved else previous
        kept, removed = _retain(table_dir, keep, latest, also_keep)
        _remove_stale_temporaries(table_dir, time.time() if now is None else now)
    return PublishResult(latest=latest, previous=previous, moved=moved, removed=removed, kept=kept)


@contextmanager
def _locked(table_dir: Path):
    """Two publishes of overlapping runs must not interleave their read of the pointer and their write of it,
    or the older one could take the pointer back. The lock is on the folder itself, so it adds no file."""
    if fcntl is None:
        yield
        return
    fd = os.open(table_dir, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)  # closing releases the lock


def _current(table_dir: Path) -> str | None:
    """The table `latest` names now, or None when there is no pointer, it is garbage, or its table is gone."""
    try:
        name = edge_depth_table.read_latest(table_dir).name
    except (FileNotFoundError, ValueError):
        return None
    return name if (table_dir / name).is_file() else None


def _retain(
    table_dir: Path, keep: int, latest: str, also_keep: Collection[str] = ()
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    names = sorted((p.name for p in table_dir.iterdir() if _TABLE_NAME.match(p.name)), reverse=True)
    keep_names = set(names[:keep]) | {latest} | set(also_keep)
    removed = tuple(sorted(n for n in names if n not in keep_names))
    for name in removed:
        (table_dir / name).unlink(missing_ok=True)
    return tuple(n for n in names if n in keep_names), removed


def _remove_stale_temporaries(table_dir: Path, now: float) -> None:
    for path in table_dir.glob(".*.tmp"):
        try:
            if now - path.stat().st_mtime > STALE_TEMPORARY_SECONDS:
                path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass  # another publisher removed it first
