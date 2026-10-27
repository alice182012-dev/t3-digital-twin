"""Flood metrics for one road segment's depth time series, per vehicle type.

Story 3 of artifacts/docs/user-stories/timescaledb-and-flood-metrics.md. Definitions follow the
architecture doc's §4.4 and glossary (artifacts/raw/T3-Digital-Twin_Architecture.md). Pure: no DB,
no I/O. extract_run.py loads the series from edge_depth and writes the result.

Every event time is a sample time from the series, never an interpolated threshold crossing, so a
value is reproducible by reading the segment's rows by hand. Its precision is the timestep spacing
(15 minutes for a constant_cycle run). Only forecast depth interpolates, and only when T+1h or T+2h
falls between two samples.

"T" is the series' first timestep, not the run name: the pipeline sets run_ts to the
earliest depth timestamp today, but older runs stored a folder time that differs from it.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Union

PRE_CLOSURE_LEAD = timedelta(hours=1)


@dataclass(frozen=True)
class DepthSeries:
    times: tuple[datetime, ...]
    depths_m: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.times:
            raise ValueError("a depth series needs at least one timestep")
        if len(self.times) != len(self.depths_m):
            raise ValueError(f"{len(self.times)} times but {len(self.depths_m)} depths")
        if any(b <= a for a, b in zip(self.times, self.times[1:])):
            raise ValueError("series times must be strictly increasing (duplicate segment rows?)")

    @property
    def start(self) -> datetime:
        return self.times[0]

    @property
    def end(self) -> datetime:
        return self.times[-1]


@dataclass(frozen=True)
class Peak:
    at: datetime
    depth_m: float
    at_window_end: bool
    """True when the maximum is the last sample: the real peak may come after the run window."""


@dataclass(frozen=True)
class NeverImpassable:
    """Depth stays below the vehicle's hard-block threshold for the whole run window."""


@dataclass(frozen=True)
class Closed:
    closed_at: datetime
    """First sample at or above the hard-block threshold."""
    pre_closure_at: datetime
    """closed_at minus PRE_CLOSURE_LEAD, clamped to the window start."""
    restored_at: datetime | None
    """First sample after the last impassable one. None when still impassable at window end."""


Passability = Union[NeverImpassable, Closed]


@dataclass(frozen=True)
class SegmentMetrics:
    window_start: datetime
    window_end: datetime
    peak: Peak | None
    """None when the segment is dry (depth 0) at every timestep."""
    recession_onset: datetime | None
    """First sample after the peak with depth below it. None when dry or never falling."""
    forecast_depth_1h_m: float | None
    """Depth at T+1h. None when T+1h is past the window end."""
    forecast_depth_2h_m: float | None
    """Depth at T+2h. None when T+2h is past the window end."""
    passability: Mapping[str, Passability]

    @property
    def time_to_peak(self) -> timedelta | None:
        return None if self.peak is None else self.peak.at - self.window_start


def extract(series: DepthSeries, impassable_from_m: Mapping[str, float]) -> SegmentMetrics:
    """impassable_from_m maps vehicle type to the depth (metres) at which that vehicle's segment
    is impassable, inclusive, the same `depth >= band_min` rule flood_areas.py routes with."""
    peak_index = _peak_index(series)
    return SegmentMetrics(
        window_start=series.start,
        window_end=series.end,
        peak=None
        if peak_index is None
        else Peak(
            at=series.times[peak_index],
            depth_m=series.depths_m[peak_index],
            at_window_end=peak_index == len(series.times) - 1,
        ),
        recession_onset=None if peak_index is None else _recession_onset(series, peak_index),
        forecast_depth_1h_m=_depth_at(series, series.start + timedelta(hours=1)),
        forecast_depth_2h_m=_depth_at(series, series.start + timedelta(hours=2)),
        passability={
            vehicle: _passability(series, threshold_m)
            for vehicle, threshold_m in impassable_from_m.items()
        },
    )


def _peak_index(series: DepthSeries) -> int | None:
    peak_depth = max(series.depths_m)
    if peak_depth <= 0:
        return None
    return series.depths_m.index(peak_depth)


def _recession_onset(series: DepthSeries, peak_index: int) -> datetime | None:
    peak_depth = series.depths_m[peak_index]
    for time, depth in zip(series.times[peak_index + 1 :], series.depths_m[peak_index + 1 :]):
        if depth < peak_depth:
            return time
    return None


def _depth_at(series: DepthSeries, time: datetime) -> float | None:
    if time > series.end:
        return None
    i = bisect_left(series.times, time)
    if series.times[i] == time:
        return series.depths_m[i]
    t0, t1 = series.times[i - 1], series.times[i]
    d0, d1 = series.depths_m[i - 1], series.depths_m[i]
    return d0 + (d1 - d0) * ((time - t0) / (t1 - t0))


def _passability(series: DepthSeries, threshold_m: float) -> Passability:
    impassable = [i for i, depth in enumerate(series.depths_m) if depth >= threshold_m]
    if not impassable:
        return NeverImpassable()
    first, last = impassable[0], impassable[-1]
    closed_at = series.times[first]
    return Closed(
        closed_at=closed_at,
        pre_closure_at=max(series.start, closed_at - PRE_CLOSURE_LEAD),
        restored_at=series.times[last + 1] if last + 1 < len(series.times) else None,
    )
