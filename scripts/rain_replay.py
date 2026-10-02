"""Replay a recorded rain event as the forecast the pipeline asks for.

An event is a list of (offset_minutes, mm_per_hour) rows, 30 minutes apart, with offset 0 at a
start time the operator picks. `cut_window` makes one from a hyetograph. `replay_intervals`
returns the same interval shape as `create_simulation.build_fixed_rain_intervals`.

Cut a new event:
    python3 rain_replay.py cut SOURCE.csv START_UTC HOURS OUT.csv

List the runs the rain gate lets through, as chains with their start times:
    python3 rain_replay.py preview EVENT.csv START_UTC THRESHOLD_MM_HR [HOURS]
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

SOURCE_RATE_COLUMN = "precipitation_mm_hr"
SOURCE_TIME_COLUMN = "timestamp_utc"
EVENT_HEADER = ["offset_minutes", "precipitation_mm_hr"]
LOCAL_ZONE = timezone(timedelta(hours=7))
# A run saves states valid 1 and 2 slots later, and a run hotstarts from a state at most 2 slots old.
# So a run hotstarts when the last simulating slot is at most 4 slots earlier, and cold-starts otherwise.
HOTSTART_REACH_SLOTS = 4


def _parse_utc(value):
    moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _iso_z(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_source(path):
    """Read a hyetograph CSV as (timestamp_utc, mm_per_hour) rows."""
    with open(path, newline="") as f:
        return [(row[SOURCE_TIME_COLUMN], float(row[SOURCE_RATE_COLUMN])) for row in csv.DictReader(f)]


def cut_window(rows, start_utc, hours):
    """Keep the rows from `start_utc` through `start_utc + hours` inclusive, with offsets in minutes from `start_utc`."""
    start = _parse_utc(start_utc)
    end = start + timedelta(hours=hours)
    stamped = [(_parse_utc(stamp), rate) for stamp, rate in rows]
    if start not in {moment for moment, _ in stamped}:
        raise ValueError(f"{_iso_z(start)} is not a row of the source")
    if end > stamped[-1][0]:
        raise ValueError(f"the window ends at {_iso_z(end)}, after the source's last row at {_iso_z(stamped[-1][0])}")
    return [(int((moment - start).total_seconds() // 60), rate) for moment, rate in stamped if start <= moment <= end]


def write_event(path, event):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(EVENT_HEADER)
        writer.writerows(event)


def load_event(path):
    with open(path, newline="") as f:
        reader = csv.reader(f)
        if next(reader) != EVENT_HEADER:
            raise ValueError(f"{path} does not have the header {','.join(EVENT_HEADER)}")
        return [(int(offset), float(rate)) for offset, rate in reader]


def _rate_at(event, offset_minutes):
    """The rate of the last sample at or before the offset. Zero before the first sample and after the last."""
    if offset_minutes < event[0][0] or offset_minutes > event[-1][0]:
        return 0.0
    return [rate for offset, rate in event if offset <= offset_minutes][-1]


def replay_intervals(event, event_start, start, duration_hours, timestep_minutes):
    """Forecast intervals from `start`, reading the event as if its offset 0 happened at `event_start`."""
    count = int((duration_hours * 60) / timestep_minutes)
    intervals = []
    for index in range(count + 1):
        moment = start + timedelta(minutes=timestep_minutes * index)
        offset = (moment - event_start).total_seconds() / 60
        intervals.append({"startTime": _iso_z(moment), "values": {"precipitationIntensity": _rate_at(event, offset)}})
    return intervals


class SlotPlan(NamedTuple):
    offset_minutes: int
    simulates: bool
    starts_chain: bool
    cold_start: bool


def plan_slots(simulates, timestep_minutes):
    """Mark chain starts and cold starts in a list of per-slot booleans."""
    slots = []
    last = None
    for index, flag in enumerate(simulates):
        starts_chain = flag and (index == 0 or not simulates[index - 1])
        cold = flag and (last is None or index - last > HOTSTART_REACH_SLOTS)
        slots.append(SlotPlan(index * timestep_minutes, flag, starts_chain, cold))
        if flag:
            last = index
    return slots


def simulating_slots(event, event_start, threshold, hours, lookahead_hours, timestep_minutes):
    """For each slot of the window, whether the rain gate lets its run through. Same test as `evaluate_rain_gate`."""
    flags = []
    for index in range(int(hours * 60 / timestep_minutes)):
        slot = event_start + timedelta(minutes=timestep_minutes * index)
        intervals = replay_intervals(event, event_start, slot, lookahead_hours, timestep_minutes)
        flags.append(max(i["values"]["precipitationIntensity"] for i in intervals) >= threshold)
    return plan_slots(flags, timestep_minutes)


def chain_lengths(slots):
    lengths = []
    for slot in slots:
        if slot.starts_chain:
            lengths.append(0)
        if slot.simulates:
            lengths[-1] += 1
    return lengths


def describe(slots, event_start, threshold):
    """One summary line, then one line per chain with local start and end times."""
    local = lambda offset: (event_start + timedelta(minutes=offset)).astimezone(LOCAL_ZONE).strftime("%Y-%m-%d %H:%M")
    lengths = chain_lengths(slots)
    lines = [f"gate {threshold:g} mm/h: {sum(s.simulates for s in slots)} of {len(slots)} runs simulate, {len(lengths)} chains"]
    starts = [s for s in slots if s.starts_chain]
    for number, (start, length) in enumerate(zip(starts, lengths), 1):
        last = start.offset_minutes + (length - 1) * (slots[1].offset_minutes - slots[0].offset_minutes)
        kind = "cold start" if start.cold_start else "hotstart"
        lines.append(f"chain {number}: {local(start.offset_minutes)} to {local(last)} +07, {length} runs, {kind}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    cut = sub.add_parser("cut")
    cut.add_argument("source")
    cut.add_argument("start_utc")
    cut.add_argument("hours", type=float)
    cut.add_argument("out")
    preview = sub.add_parser("preview")
    preview.add_argument("event")
    preview.add_argument("start_utc")
    preview.add_argument("threshold", type=float)
    preview.add_argument("hours", nargs="?", type=float, default=48)
    args = parser.parse_args(argv)
    if args.command == "cut":
        event = cut_window(read_source(args.source), args.start_utc, args.hours)
        write_event(args.out, event)
        print(f"{args.out}: {len(event)} rows, {sum(rate for _, rate in event) * 0.5:.1f} mm, peak {max(rate for _, rate in event)} mm/h")
    else:
        event_start = _parse_utc(args.start_utc)
        slots = simulating_slots(load_event(args.event), event_start, args.threshold, args.hours, 2, 15)
        print("\n".join(describe(slots, event_start, args.threshold)))


if __name__ == "__main__":
    main()
