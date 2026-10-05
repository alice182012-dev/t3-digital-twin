"""Writes the shared fixture of the edge depth table (US-043): a table of 3,000 edges by 9 steps and a JSON file
with its header and every value. The Java reader and the Python reader must both return those values.

Usage: python golden_fixture.py [--write]

Without --write it prints what it would write. The files go into the test resources of the Java module,
because the Docker build of that module sees only its own folder. test_golden_fixture.py fails when they differ
from what this generates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edge_depth_table import TableHeader, write_table

RESOURCES = Path(__file__).resolve().parents[2] / "java/time-aware-routing/src/test/resources/edge-depth"

EDGE_COUNT = 3000
STEP_COUNT = 9
RUN_NAME = "20261001T000000"
GRAPH_HASH = hashlib.sha256(b"edge-depth-golden-fixture").hexdigest()
FIRST_STEP = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)


def depths() -> list[list[int]]:
    """A formula for most rows, and rows for the values a reader gets wrong: 0, a byte boundary, the signed
    16-bit boundary, and the largest value."""
    rows = [[(edge * 7 + step * 13) % 65536 for step in range(STEP_COUNT)] for edge in range(EDGE_COUNT)]
    rows[0] = [0] * STEP_COUNT
    rows[1] = [65535] * STEP_COUNT
    rows[2] = [0, 1, 255, 256, 257, 1000, 32767, 32768, 65535]
    rows[EDGE_COUNT - 1] = [65535, 0, 65535, 0, 1, 255, 256, 32768, 65534]
    return rows


def build() -> tuple[bytes, dict]:
    rows = depths()
    step_times = tuple(FIRST_STEP + timedelta(minutes=15 * i) for i in range(STEP_COUNT))
    header = TableHeader(GRAPH_HASH, RUN_NAME, step_times, EDGE_COUNT)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "golden.bin"
        write_table(path, header, rows)
        table_bytes = path.read_bytes()
    expected = {
        "graph_hash": GRAPH_HASH,
        "run_name": RUN_NAME,
        "edge_count": EDGE_COUNT,
        "step_count": STEP_COUNT,
        "step_times_epoch": [int(t.timestamp()) for t in step_times],
        "depths_cm": rows,
    }
    return table_bytes, expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    table_bytes, expected = build()
    if not args.write:
        print(f"would write {len(table_bytes)} bytes of golden.bin and golden.json to {RESOURCES}")
        return 0
    RESOURCES.mkdir(parents=True, exist_ok=True)
    (RESOURCES / "golden.bin").write_bytes(table_bytes)
    (RESOURCES / "golden.json").write_text(json.dumps(expected, separators=(",", ":")) + "\n")
    print(f"wrote {RESOURCES}/golden.bin ({len(table_bytes)} bytes) and golden.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
