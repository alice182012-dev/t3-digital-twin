#!/usr/bin/env python3
"""Timing report of the edge depth table task (task 9c) over the runs of flood_mapping_full, for US-045.

Reads the output of table_timing.ps1, one run per line, nine fields joined by `~`:

    run_id, logical_date, end of 3_calculate_depth, start and end of 9_build_flood_tiles (all UTC ISO, empty when the
    task did not succeed), state of 9c_build_edge_depth_table, its start and end, and the XCom `edge_depth_table` it
    pushed (JSON, empty when none). 9c runs in the routing_adapter run that the run's 9b asset event triggered, so
    its fields are empty until that run exists, and the run counts as pending.

The limit (US-045, set by the user on 2026-10-02): the table task runs beside the tile task, never delays it, and ends
within 5 minutes of the end of 3_calculate_depth. The report passes (exit code 0) when at least one run has a table, no
table task ended later than the limit, none was a failure, and none held up the tile task. A run that the rain gate
skipped is counted and left out. A run whose 9c has not finished is pending and does not decide the verdict.

"Held up the tile task" means 9c ran at any time between the end of 3_calculate_depth, when the tile task could start,
and the start of the tile task. With one worker slot (AIRFLOW__CELERY__WORKER_CONCURRENCY=1) that is the case when 9c took
the slot first. With more slots a tile task that waited for another reason is flagged too, so read the overlap with the
worker concurrency in mind.

    docker exec airflow_new-airflow-worker-1 python /opt/airflow/scripts/edge_depth/table_timing.py --limit-minutes 5 < rows
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TextIO

SEP = "~"
FIELDS = 9
LOCAL = timezone(timedelta(hours=7))
FAILED_STATES = {"failed", "upstream_failed"}
PENDING_STATES = {"", "running", "queued", "scheduled", "up_for_retry", "restarting", "deferred", "up_for_reschedule"}


@dataclass(frozen=True)
class Row:
    run_id: str
    logical_date: datetime
    calc_end: datetime | None
    tiles_start: datetime | None
    tiles_end: datetime | None
    c_state: str | None
    c_start: datetime | None
    c_end: datetime | None
    report: dict | None


@dataclass(frozen=True)
class Run:
    row: Row
    after_calc_s: float
    task_s: float | None
    tile_wait_s: float | None
    overlap_s: float
    over_limit: bool
    delayed_tiles: bool
    edge_count: int | None
    size_bytes: int | None
    wet_max: int | None


@dataclass
class Result:
    runs: list[Run]
    skipped: int
    failed: int
    pending: int
    failed_rows: list[Row]
    over: int
    delayed: int
    worst_s: float | None
    median_s: float | None
    best_s: float | None

    @property
    def exit_code(self) -> int:
        ok = bool(self.runs) and self.over == 0 and self.delayed == 0 and self.failed == 0
        return 0 if ok else 1


def _moment(text: str) -> datetime | None:
    text = text.strip()
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def _report(text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None
    value = json.loads(text)
    return json.loads(value) if isinstance(value, str) else value


def parse_lines(text: str) -> list[Row]:
    rows = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        fields = raw.split(SEP)
        if len(fields) != FIELDS:
            raise ValueError(f"not a table timing line ({len(fields)} fields, {FIELDS} expected): {raw[:200]}")
        try:
            logical = _moment(fields[1])
            if logical is None:
                raise ValueError("no logical date")
            rows.append(Row(fields[0], logical, _moment(fields[2]), _moment(fields[3]), _moment(fields[4]),
                            fields[5].strip() or None, _moment(fields[6]), _moment(fields[7]), _report(fields[8])))
        except ValueError as error:
            raise ValueError(f"not a table timing line ({error}): {raw[:200]}") from error
    return rows


def _seconds(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds()


def analyse(rows: list[Row], limit_s: float = 300.0) -> Result:
    runs: list[Run] = []
    failed_rows: list[Row] = []
    skipped = pending = 0
    for row in rows:
        state = row.c_state or ""
        if row.calc_end is None and (state == "" or state == "skipped"):
            skipped += 1
            continue
        if state in FAILED_STATES:
            failed_rows.append(row)
            continue
        if state in PENDING_STATES or row.calc_end is None or row.c_end is None or row.c_start is None:
            pending += 1
            continue
        if state != "success":
            failed_rows.append(row)
            continue
        after = _seconds(row.c_end, row.calc_end)
        wait = _seconds(row.tiles_start, row.calc_end) if row.tiles_start else None
        overlap = 0.0
        if row.tiles_start:
            overlap = max(0.0, _seconds(min(row.c_end, row.tiles_start), max(row.c_start, row.calc_end)))
        report = row.report or {}
        wet = report.get("wet_edges") or []
        runs.append(Run(row, after, _seconds(row.c_end, row.c_start), wait, overlap, after > limit_s, overlap > 1.0,
                        report.get("edge_count"), report.get("bytes"), max(wet) if wet else None))
    afters = [r.after_calc_s for r in runs]
    return Result(
        runs, skipped, len(failed_rows), pending, failed_rows,
        sum(r.over_limit for r in runs), sum(r.delayed_tiles for r in runs),
        max(afters) if afters else None, statistics.median(afters) if afters else None, min(afters) if afters else None,
    )


def _slot(moment: datetime) -> str:
    return moment.astimezone(LOCAL).strftime("%m-%d %H:%M")


def render(result: Result, limit_s: float = 300.0) -> str:
    lines = [f"9c after 3_calculate_depth, limit {limit_s / 60:g} min. Slot times are +07.", ""]
    lines.append(f"{'slot':<12} {'9c s':>6} {'after 3 (min)':>14} {'tile wait s':>12} {'overlap s':>10} {'edges':>7} {'bytes':>9} {'wet max':>8}  note")
    for run in result.runs:
        notes = []
        if run.over_limit:
            notes.append("OVER the limit")
        if run.delayed_tiles:
            notes.append("held up the tile task")
        lines.append(
            f"{_slot(run.row.logical_date):<12} {run.task_s:>6.1f} {run.after_calc_s / 60:>14.2f} "
            f"{'' if run.tile_wait_s is None else format(run.tile_wait_s, '.1f'):>12} {run.overlap_s:>10.1f} "
            f"{run.edge_count if run.edge_count is not None else '':>7} {run.size_bytes if run.size_bytes is not None else '':>9} "
            f"{run.wet_max if run.wet_max is not None else '':>8}  {', '.join(notes)}"
        )
    for row in result.failed_rows:
        lines.append(f"{_slot(row.logical_date):<12} 9c state {row.c_state}: no table for this run")
    lines.append("")
    lines.append(f"runs with a table {len(result.runs)}, failed {result.failed}, pending {result.pending}, skipped by the rain gate {result.skipped}")
    if result.runs:
        lines.append(
            f"end of 9c after 3_calculate_depth: worst {result.worst_s / 60:.2f} min, median {result.median_s / 60:.2f}, "
            f"best {result.best_s / 60:.2f}; over the limit {result.over}; held up the tile task {result.delayed}"
        )
    if result.exit_code == 0:
        lines.append(f"PASS: all {len(result.runs)} runs ended within {limit_s / 60:g} minutes of 3_calculate_depth and none held up the tile task")
    elif not result.runs and not result.failed:
        lines.append("FAIL: no run with a table to judge")
    else:
        lines.append(f"FAIL: {result.over} over the limit, {result.delayed} held up the tile task, {result.failed} without a table")
    return "\n".join(lines)


def main(argv: list[str] | None = None, stdin: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--limit-minutes", type=float, default=5.0)
    args = parser.parse_args(argv)
    limit_s = args.limit_minutes * 60
    try:
        rows = parse_lines((stdin or sys.stdin).read())
    except ValueError as error:
        print(f"FAIL: {error}")
        return 1
    result = analyse(rows, limit_s)
    print(render(result, limit_s))
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
