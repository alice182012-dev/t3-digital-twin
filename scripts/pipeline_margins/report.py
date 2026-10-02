#!/usr/bin/env python3
"""Report the step-1 margin of every run of the rain replay (US-065).

Input is the output of `run_margins.sh`, one run per line: slot (MM-DD HH:MM, +07), trigger, depth, raster, and
tiles minutes, then the margin in minutes. A run that the rain gate skipped has empty fields. The margin is how
long before step 1 became "now" the tile task ended. A negative margin means it was late. Step 2 is published 1 to
1.3 minutes after step 1, so the margin understates the margin of step 1 by about that much.

    run_margins.sh 250 | report.py --event ../rain_events/hanoi_20251005_48h.csv --start 2026-10-02T09:00:00Z --threshold 0.01

With --event, --start, and --threshold the report also lists the runs the replay should have simulated and
did not. Exit code 0 only if no run is late, none is missing, and at least one run has a margin.
"""
import argparse
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rain_replay  # noqa: E402

SLOT_FORMAT = "%m-%d %H:%M"
STEP = timedelta(minutes=15)


@dataclass(frozen=True)
class Row:
    slot: str
    trigger: float | None
    depth: float | None
    raster: float | None
    tiles: float | None
    margin: float | None


@dataclass
class Trend:
    first_slot: str
    last_slot: str
    runs: int
    slope: float | None
    last_margin: float
    runs_to_zero: float | None


@dataclass
class Judgement:
    margins: list[float] = field(default_factory=list)
    worst: float | None = None
    worst_slot: str | None = None
    median: float | None = None
    best: float | None = None
    late: list[Row] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    trends: list[Trend] = field(default_factory=list)
    passed: bool = False


def _time(slot):
    return datetime.strptime(f"2024-{slot}", "%Y-%m-%d %H:%M")


def _number(field_text):
    return float(field_text) if field_text.strip() else None


def parse_rows(text):
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.rstrip("\n").split(" ")
        try:
            if len(parts) != 7:
                raise ValueError
            _time(" ".join(parts[:2]))
            rows.append(Row(" ".join(parts[:2]), *(_number(p) for p in parts[2:])))
        except ValueError:
            raise ValueError(f"cannot read this line as a run: {line[:200]}") from None
    return rows


def _trend(chain):
    margins = [m for _, m in chain]
    slope = None
    if len(margins) >= 3:
        xs = range(len(margins))
        mean_x, mean_y = statistics.fmean(xs), statistics.fmean(margins)
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, margins)) / sum((x - mean_x) ** 2 for x in xs)
    reaches = margins[-1] / -slope if slope is not None and slope < 0 and margins[-1] > 0 else None
    return Trend(chain[0][0], chain[-1][0], len(chain), slope, margins[-1], reaches)


def judge(rows, expected=None, min_margin=0.0, since=None, until=None):
    result = Judgement()
    rows = [
        r
        for r in rows
        if (since is None or _time(r.slot) >= _time(since)) and (until is None or _time(r.slot) <= _time(until))
    ]
    measured = [(r.slot, r.margin) for r in rows if r.margin is not None]
    result.margins = [m for _, m in measured]
    if measured:
        worst_slot, worst = min(measured, key=lambda item: item[1])
        result.worst, result.worst_slot = worst, worst_slot
        result.median, result.best = statistics.median(result.margins), max(result.margins)
    result.late = [r for r in rows if r.margin is not None and r.margin < min_margin]
    if expected is not None:
        last_row = max((r.slot for r in rows), key=_time, default=None)
        stop = until or last_row
        have = {slot for slot, _ in measured}
        result.missing = [
            slot
            for slot in expected
            if stop is not None
            and (since is None or _time(slot) >= _time(since))
            and _time(slot) <= _time(stop)
            and slot not in have
        ]
    chain = []
    for slot, margin in sorted(measured, key=lambda item: _time(item[0])):
        if chain and _time(slot) - _time(chain[-1][0]) != STEP:
            result.trends.append(_trend(chain))
            chain = []
        chain.append((slot, margin))
    if chain:
        result.trends.append(_trend(chain))
    result.passed = bool(measured) and not result.late and not result.missing
    return result


def expected_slots(event, event_start, threshold, hours=48, lookahead_hours=2):
    """The slots the replay should simulate, as `MM-DD HH:MM` in +07, the form run_margins.sh prints."""
    slots = rain_replay.simulating_slots(event, event_start, threshold, hours, lookahead_hours, 15)
    return [
        (event_start + timedelta(minutes=s.offset_minutes)).astimezone(rain_replay.LOCAL_ZONE).strftime(SLOT_FORMAT)
        for s in slots
        if s.simulates
    ]


def render(result, min_margin):
    lines = [f"runs with a margin: {len(result.margins)}"]
    if result.margins:
        lines.append(
            f"margin to the end of the tile task in minutes: worst {result.worst:+.1f} at {result.worst_slot}, "
            f"median {result.median:+.1f}, best {result.best:+.1f}"
        )
    late = ", ".join(f"{r.slot} ({r.margin:+.1f})" for r in result.late) or "none"
    lines.append(f"late runs (margin below {min_margin:.1f}): {late}")
    lines.append(f"missing runs: {', '.join(result.missing) or 'none'}")
    for number, trend in enumerate(result.trends, 1):
        text = f"chain {number}: {trend.first_slot} to {trend.last_slot}, {trend.runs} runs"
        if trend.slope is not None:
            text += f", margin slope {trend.slope:+.2f} minutes per run, last margin {trend.last_margin:+.1f}"
            if trend.runs_to_zero is not None:
                text += f", reaches 0 in about {trend.runs_to_zero:.0f} more runs"
        lines.append(text)
    lines.append("verdict: " + ("PASS" if result.passed else "FAIL"))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rows", nargs="?", default="-", help="the output of run_margins.sh. Default: standard input")
    parser.add_argument("--event")
    parser.add_argument("--start", help="UTC time of the event's offset 0, for example 2026-10-02T09:00:00Z")
    parser.add_argument("--threshold", type=float, help="the rain gate in mm/h")
    parser.add_argument("--min-margin", type=float, default=0.0)
    parser.add_argument("--since", help="first slot to judge, as 'MM-DD HH:MM' in +07")
    parser.add_argument("--until", help="last slot to judge. Default: the last slot with a row")
    args = parser.parse_args(argv)
    text = sys.stdin.read() if args.rows == "-" else Path(args.rows).read_text()
    try:
        rows = parse_rows(text)
        expected = None
        if args.event:
            if not (args.start and args.threshold is not None):
                parser.error("--event needs --start and --threshold")
            start = rain_replay._parse_utc(args.start)
            expected = expected_slots(rain_replay.load_event(args.event), start, args.threshold)
    except ValueError as error:
        print(error)
        return 1
    result = judge(rows, expected, args.min_margin, args.since, args.until)
    print(render(result, args.min_margin))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
