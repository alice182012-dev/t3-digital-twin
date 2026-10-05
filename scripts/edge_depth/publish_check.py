"""Checks atomic publish and retention on the real table folder, for US-042.

Usage: python publish_check.py [--table-dir DIR] [--publishes 40] [--keep 3]

It works in a scratch folder inside the table folder, so it meets the same file system (on the server, the
Docker volume edge-depth-tables) and the real `latest` and tables are not touched. A reader in its own process
polls the scratch pointer and reads the table it names, in a loop, while this process publishes tables of the
real size (67,833 edges by 8 steps, about 1 MB) one after another. The check passes when:

- every read is a whole table, the header names the run of the file the pointer named, and its depths are the
  ones written for that run;
- the reader saw the pointer move;
- when the last publish is done, `latest` names the newest table and exactly `keep` tables are left.

Exit code 1 means a check failed.
"""

from __future__ import annotations

import argparse
import multiprocessing
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import edge_depth_table
import publish_edge_depth

EDGES = 67833
STEPS = 8
BASE = datetime(2026, 10, 5, 0, 0)
SCRATCH_PREFIX = ".publish-check-"


def run_name(index: int) -> str:
    return (BASE + timedelta(minutes=15 * index)).strftime("%Y%m%dT%H%M%S")


def make_table(directory: Path, index: int) -> str:
    """A table of the real size whose every depth is `index` centimetres (mod 65536)."""
    name = run_name(index)
    header = edge_depth_table.TableHeader(
        graph_hash="c" * 64,
        run_name=name,
        step_times=tuple((BASE + timedelta(minutes=15 * s)).replace(tzinfo=timezone.utc) for s in range(STEPS)),
        edge_count=EDGES,
    )
    row = (index,) * STEPS
    edge_depth_table.write_table(directory / f"{name}.bin", header, (row for _ in range(EDGES)))
    return f"{name}.bin"


def poll(directory: str, stop, results) -> None:
    reads = failures = 0
    runs = set()
    first_failure = ""
    probe = (0, EDGES // 2, EDGES - 1)
    while not stop.is_set():
        try:
            table = edge_depth_table.read_latest_table(Path(directory))
            index = table.edge_depths_cm(0)[0]
            ok = table.header.run_name == run_name(index) and table.header.edge_count == EDGES
            ok = ok and all(table.edge_depths_cm(e) == (index,) * STEPS for e in probe)
            runs.add(index)
            reads += 1
            if not ok:
                failures += 1
                first_failure = first_failure or f"read of run {index} did not match what was written"
        except Exception as e:  # noqa: BLE001 - any failed read is a finding
            failures += 1
            first_failure = first_failure or repr(e)
    results.put((reads, failures, sorted(runs), first_failure))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--table-dir", default="/opt/airflow/edge_depth_tables")
    parser.add_argument("--publishes", type=int, default=40)
    parser.add_argument("--keep", type=int, default=publish_edge_depth.DEFAULT_KEEP)
    args = parser.parse_args(argv)

    table_dir = Path(args.table_dir)
    scratch = table_dir / f"{SCRATCH_PREFIX}{int(time.time())}"
    scratch.mkdir(parents=True)
    failed = []
    try:
        publish_edge_depth.publish_table(scratch, make_table(scratch, 0), keep=args.keep)
        context = multiprocessing.get_context("fork")
        stop, results = context.Event(), context.Queue()
        reader = context.Process(target=poll, args=(str(scratch), stop, results))
        reader.start()
        started = time.monotonic()
        try:
            for index in range(1, args.publishes + 1):
                publish_edge_depth.publish_table(scratch, make_table(scratch, index), keep=args.keep)
            time.sleep(0.5)
        finally:
            stop.set()
            reads, failures, runs, first_failure = results.get(timeout=120)
            reader.join(timeout=60)
        seconds = time.monotonic() - started

        latest = edge_depth_table.read_latest(scratch).name
        tables = sorted(p.name for p in scratch.iterdir() if p.suffix == ".bin")
        size = (scratch / latest).stat().st_size
        print(f"table folder: {table_dir}")
        print(f"published {args.publishes + 1} tables of {size} bytes in {seconds:.1f} s, keep {args.keep}")
        print(f"reader (own process): {reads} reads, {failures} failed, saw {len(runs)} different runs")
        print(f"latest: {latest}   tables left: {len(tables)}")

        if failures:
            failed.append(f"{failures} reads failed, the first: {first_failure}")
        if reads == 0 or len(runs) < 2:
            failed.append("the reader did not see the pointer move")
        if latest != f"{run_name(args.publishes)}.bin":
            failed.append(f"latest is {latest}, expected {run_name(args.publishes)}.bin")
        if len(tables) != args.keep:
            failed.append(f"{len(tables)} tables left, expected {args.keep}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if failed:
        print("FAIL: " + "; ".join(failed))
        return 1
    print("PASS: every read was a whole table, the pointer only moved forward, and retention kept the newest tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
