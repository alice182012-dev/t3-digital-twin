"""Replay a recorded rain event as the forecast the pipeline asks for.

An event is a list of (offset_minutes, mm_per_hour) rows, 30 minutes apart, with offset 0 at a
start time the operator picks. `cut_window` makes one from a hyetograph. `replay_intervals`
returns the same interval shape as `create_simulation.build_fixed_rain_intervals`.

Cut a new event:
    python3 rain_replay.py cut SOURCE.csv START_UTC HOURS OUT.csv

List the runs the rain gate lets through, as chains with their start times:
    python3 rain_replay.py preview EVENT.csv START_UTC THRESHOLD_MM_HR [HOURS]

Print the first 15-minute slot at least LEAD_MINUTES after NOW_UTC:
    python3 rain_replay.py next-slot NOW_UTC LEAD_MINUTES

Check that a replay setting can run, and print its event, runs, chains, and unpause time:
    python3 rain_replay.py check EVENT.csv START_UTC THRESHOLD_MM_HR

Print the rain mode that this environment selects: live, replay, or fixed-rate:
    python3 rain_replay.py status [--expect-mode MODE] [--expect-start START_UTC]

`check` and `status` exit with code 1 and a one-line reason when the setting cannot run, or when the
status differs from an expected value.
"""
import argparse
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

SOURCE_RATE_COLUMN = "precipitation_mm_hr"
SOURCE_TIME_COLUMN = "timestamp_utc"
EVENT_HEADER = ["offset_minutes", "precipitation_mm_hr"]
LOCAL_ZONE = timezone(timedelta(hours=7))
SLOT_MINUTES = 15
LOOKAHEAD_HOURS = 2
# compose.yml passes ${FLOOD_RAIN_THRESHOLD_MM_HR:-5}, so a blank gate is 5 in the worker.
DEFAULT_GATE_MM_HR = "5"
# A run saves states valid 1 and 2 slots later, and a run hotstarts from a state at most 2 slots old.
# So a run hotstarts when the last simulating slot is at most 4 slots earlier, and cold-starts otherwise.
HOTSTART_REACH_SLOTS = 4


class ReplaySetting(NamedTuple):
    event_path: str
    start: datetime
    gate_mm_hr: float


def _parse_utc(value):
    moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _iso_z(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _local(moment):
    return moment.astimezone(LOCAL_ZONE).strftime("%Y-%m-%d %H:%M")


def _slot_floor(moment):
    utc = moment.astimezone(timezone.utc)
    return utc.replace(minute=utc.minute - utc.minute % SLOT_MINUTES, second=0, microsecond=0)


def next_slot(now, lead_minutes):
    """The first slot at or after `now + lead_minutes`."""
    earliest = now.astimezone(timezone.utc) + timedelta(minutes=lead_minutes)
    floor = _slot_floor(earliest)
    return floor if floor == earliest else floor + timedelta(minutes=SLOT_MINUTES)


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


def total_mm(event):
    step_hours = (event[1][0] - event[0][0]) / 60
    return sum(rate for _, rate in event) * step_hours


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


def parse_start(value):
    try:
        return _parse_utc(value)
    except ValueError:
        raise ValueError(f"the start {value!r} is not a time") from None


def parse_gate(value):
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"the gate {value!r} is not a number") from None


def load_replay(setting):
    """The event of a setting and the plan of its runs. ValueError with a one-line reason when it cannot replay."""
    if setting.start != _slot_floor(setting.start):
        raise ValueError(f"the start {_iso_z(setting.start)} is not on a {SLOT_MINUTES}-minute slot")
    try:
        event = load_event(setting.event_path)
    except StopIteration:
        raise ValueError(f"{setting.event_path} does not load: it is empty") from None
    except (OSError, ValueError) as error:
        raise ValueError(f"{setting.event_path} does not load: {error}") from None
    if len(event) < 2:
        raise ValueError(f"{setting.event_path} does not load: it has fewer than two rows")
    hours = event[-1][0] / 60
    slots = simulating_slots(event, setting.start, setting.gate_mm_hr, hours, LOOKAHEAD_HOURS, SLOT_MINUTES)
    if not any(slot.simulates for slot in slots):
        raise ValueError(f"gate {setting.gate_mm_hr:g} mm/h: no run of the event simulates")
    return event, slots


def _event_line(path, event):
    peak = max(rate for _, rate in event)
    return f"event {path}: {len(event)} rows, {total_mm(event):.1f} mm, peak {peak:.1f} mm/h"


def check_lines(setting):
    event, slots = load_replay(setting)
    return [
        _event_line(setting.event_path, event),
        *describe(slots, setting.start, setting.gate_mm_hr),
        f"unpause flood_mapping_full before {_local(setting.start)} +07 ({_iso_z(setting.start)})",
    ]


def read_rain_env(env):
    """The rain that `env` selects: ("live", None), ("fixed-rate", mm_per_hour), or ("replay", ReplaySetting).

    Rejects the half-set or mixed combination that `create_simulation.get_rain_forecast` rejects, with its message.
    """
    replay_file = env.get("FLOOD_TEST_RAIN_CSV", "").strip()
    replay_start = env.get("FLOOD_TEST_RAIN_START", "").strip()
    test_rain = env.get("FLOOD_TEST_RAIN_MM_HR", "").strip()
    if bool(replay_file) != bool(replay_start) or (replay_file and test_rain):
        raise ValueError(
            "Set FLOOD_TEST_RAIN_CSV together with FLOOD_TEST_RAIN_START and without FLOOD_TEST_RAIN_MM_HR, "
            "or set none of them"
        )
    if replay_file:
        gate = env.get("FLOOD_RAIN_THRESHOLD_MM_HR", "").strip() or DEFAULT_GATE_MM_HR
        return "replay", ReplaySetting(replay_file, parse_start(replay_start), parse_gate(gate))
    if test_rain:
        return "fixed-rate", parse_gate(test_rain)
    return "live", None


def status_lines(mode, detail, now):
    if mode == "live":
        return ["mode live"]
    if mode == "fixed-rate":
        return ["mode fixed-rate", f"rate {detail:g} mm/h"]
    event, slots = load_replay(detail)
    simulating = [detail.start + timedelta(minutes=slot.offset_minutes) for slot in slots if slot.simulates]
    slot = _slot_floor(now)
    rate = _rate_at(event, (slot - detail.start).total_seconds() / 60)
    return [
        "mode replay",
        _event_line(detail.event_path, event),
        f"start {_iso_z(detail.start)} ({_local(detail.start)} +07)",
        f"gate {detail.gate_mm_hr:g} mm/h: {len(simulating)} of {len(slots)} runs simulate, "
        f"first {_local(simulating[0])} +07, last {_local(simulating[-1])} +07",
        f"slot {_iso_z(slot)} rate {rate:g} mm/h, next slot {_iso_z(slot + timedelta(minutes=SLOT_MINUTES))}",
    ]


def _status(expect_mode, expect_start):
    mode, detail = read_rain_env(os.environ)
    print("\n".join(status_lines(mode, detail, datetime.now(timezone.utc))))
    if expect_mode and mode != expect_mode:
        raise ValueError(f"mode is {mode}, expected {expect_mode}")
    if expect_start:
        actual = _iso_z(detail.start) if mode == "replay" else "unset"
        expected = _iso_z(parse_start(expect_start))
        if actual != expected:
            raise ValueError(f"start is {actual}, expected {expected}")


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
    slot = sub.add_parser("next-slot")
    slot.add_argument("now_utc")
    slot.add_argument("lead_minutes", type=int)
    check = sub.add_parser("check")
    check.add_argument("event")
    check.add_argument("start_utc")
    check.add_argument("threshold")
    status = sub.add_parser("status")
    status.add_argument("--expect-mode", choices=["live", "replay", "fixed-rate"])
    status.add_argument("--expect-start")
    args = parser.parse_args(argv)
    if args.command == "cut":
        event = cut_window(read_source(args.source), args.start_utc, args.hours)
        write_event(args.out, event)
        print(f"{args.out}: {len(event)} rows, {total_mm(event):.1f} mm, peak {max(rate for _, rate in event)} mm/h")
    elif args.command == "preview":
        event_start = _parse_utc(args.start_utc)
        slots = simulating_slots(load_event(args.event), event_start, args.threshold, args.hours, LOOKAHEAD_HOURS, SLOT_MINUTES)
        print("\n".join(describe(slots, event_start, args.threshold)))
    elif args.command == "next-slot":
        print(_iso_z(next_slot(_parse_utc(args.now_utc), args.lead_minutes)))
    else:
        try:
            if args.command == "check":
                setting = ReplaySetting(args.event, parse_start(args.start_utc), parse_gate(args.threshold))
                print("\n".join(check_lines(setting)))
            else:
                _status(args.expect_mode, args.expect_start)
        except ValueError as error:
            sys.exit(str(error))


if __name__ == "__main__":
    main()
