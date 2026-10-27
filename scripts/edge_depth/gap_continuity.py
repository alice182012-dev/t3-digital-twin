"""Checks that the flood a run starts from matches what the run before it forecast for the same moment (US-102).

Each edge depth table holds one run. Run N starts one slot after run N-1, so the first step of run N is a step that
run N-1 already forecast. If the model kept its state (a hotstart), the number of wet edges at that step is close to
the number the previous run forecast. After a cold start the flood is lost, and the ratio falls far under 1 (BL-028:
about 0.30 in the second replay).

Usage: python gap_continuity.py TABLE_DIR [--first RUN] [--last RUN] [--wet-cm 1] [--low 0.8] [--high 1.25]

RUN is a table name without .bin, for example 20261009T193000. Exit code 1 means a ratio is outside the band.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import edge_depth_table

DEFAULT_WET_CM = 1
DEFAULT_LOW = 0.8
DEFAULT_HIGH = 1.25


@dataclass(frozen=True)
class Link:
    """The wet edges of a run at its first step, against the previous run's forecast for the same step."""

    run: str
    previous_run: str
    wet_now: int
    wet_forecast: int

    @property
    def ratio(self) -> Optional[float]:
        return self.wet_now / self.wet_forecast if self.wet_forecast else None

    def inside(self, low: float, high: float) -> bool:
        if self.ratio is None:
            return self.wet_now == 0
        return low <= self.ratio <= high


def wet_edges(table: edge_depth_table.EdgeDepthTable, step: int, wet_cm: int) -> int:
    return sum(1 for edge in range(table.header.edge_count) if table.depth_cm(edge, step) >= wet_cm)


def link(previous: edge_depth_table.EdgeDepthTable, table: edge_depth_table.EdgeDepthTable, wet_cm: int) -> Link:
    first_step = table.header.step_times[0]
    if first_step not in previous.header.step_times:
        raise ValueError(f"run {previous.header.run_name} did not forecast {first_step.isoformat()}, the first step of {table.header.run_name}")
    return Link(
        run=table.header.run_name,
        previous_run=previous.header.run_name,
        wet_now=wet_edges(table, 0, wet_cm),
        wet_forecast=wet_edges(previous, previous.header.step_times.index(first_step), wet_cm),
    )


def links(tables: list, wet_cm: int = DEFAULT_WET_CM) -> list:
    return [link(previous, table, wet_cm) for previous, table in zip(tables, tables[1:])]


def load_runs(directory: Path, first: Optional[str], last: Optional[str]) -> list:
    paths = sorted(p for p in directory.glob("*.bin") if (first is None or p.stem >= first) and (last is None or p.stem <= last))
    return [edge_depth_table.read_table(p) for p in paths]


def format_line(item: Link, low: float, high: float) -> str:
    ratio = "n/a" if item.ratio is None else f"{item.ratio:.2f}"
    verdict = "ok" if item.inside(low, high) else "OUTSIDE"
    return f"{item.run}  wet {item.wet_now:6d}  forecast by {item.previous_run} {item.wet_forecast:6d}  ratio {ratio:>5}  {verdict}"


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Wet-edge continuity between consecutive runs.")
    parser.add_argument("table_dir", type=Path)
    parser.add_argument("--first")
    parser.add_argument("--last")
    parser.add_argument("--wet-cm", type=int, default=DEFAULT_WET_CM)
    parser.add_argument("--low", type=float, default=DEFAULT_LOW)
    parser.add_argument("--high", type=float, default=DEFAULT_HIGH)
    args = parser.parse_args(argv)
    tables = load_runs(args.table_dir, args.first, args.last)
    if len(tables) < 2:
        print(f"need at least 2 tables in {args.table_dir}, found {len(tables)}", file=sys.stderr)
        return 2
    result = links(tables, args.wet_cm)
    print(f"wet edge = depth of {args.wet_cm} cm or more. Band {args.low:g} to {args.high:g}.")
    for item in result:
        print(format_line(item, args.low, args.high))
    outside = [item for item in result if not item.inside(args.low, args.high)]
    print(f"{len(result) - len(outside)} of {len(result)} runs inside the band")
    return 1 if outside else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
