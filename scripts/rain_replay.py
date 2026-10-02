"""Replay a recorded rain event as the forecast the pipeline asks for.

An event is a list of (offset_minutes, mm_per_hour) rows, 30 minutes apart, with offset 0 at a
start time the operator picks. `cut_window` makes one from a hyetograph. `replay_intervals`
returns the same interval shape as `create_simulation.build_fixed_rain_intervals`.

Cut a new event:
    python3 rain_replay.py SOURCE.csv START_UTC HOURS OUT.csv
"""
import csv
import sys
from datetime import datetime, timedelta, timezone

SOURCE_RATE_COLUMN = "precipitation_mm_hr"
SOURCE_TIME_COLUMN = "timestamp_utc"
EVENT_HEADER = ["offset_minutes", "precipitation_mm_hr"]


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
        writer = csv.writer(f)
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


if __name__ == "__main__":
    source, start_utc, hours, out = sys.argv[1:5]
    event = cut_window(read_source(source), start_utc, float(hours))
    write_event(out, event)
    print(f"{out}: {len(event)} rows, {sum(rate for _, rate in event) * 0.5:.1f} mm, peak {max(rate for _, rate in event)} mm/h")
