"""Re-walk a planned route over the edge depth table with the arrival time of each edge (US-091).

The route was planned on the depth of one forecast step. The re-walk enters each edge at its free-flow arrival
time and reads the depth the traveller meets there. Arrival times fall between forecast steps, so three rules
pick the depth, and a result reports all three side by side. A depth equal to the limit is a violation, the same
rule as the sticky closure (scripts/routing_reference/sticky_reference.py). Pure: no I/O.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Sequence

DepthLookup = Callable[[int, int], int]


class StepRule(Enum):
    AT_OR_BEFORE = "at_or_before"
    NEAREST = "nearest"
    WORSE_OF_TWO = "worse_of_two"


def steps_for(rule: StepRule, step_seconds: Sequence[float], arrival_s: float) -> tuple[int, ...]:
    """The step indexes a rule reads for an arrival. An arrival before the first step reads the first step and
    one after the last step reads the last. An arrival exactly on a step reads that step only."""
    after = bisect.bisect_right(step_seconds, arrival_s)
    before = max(after - 1, 0)
    if after >= len(step_seconds) or step_seconds[before] == arrival_s or arrival_s < step_seconds[0]:
        return (before,)
    if rule is StepRule.AT_OR_BEFORE:
        return (before,)
    if rule is StepRule.NEAREST:
        return (before,) if arrival_s - step_seconds[before] <= step_seconds[after] - arrival_s else (after,)
    return (before, after)


@dataclass(frozen=True)
class Route:
    edge_ids: tuple[int, ...]
    edge_seconds: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.edge_ids) != len(self.edge_seconds):
            raise ValueError(f"{len(self.edge_ids)} edges but {len(self.edge_seconds)} travel times")

    @classmethod
    def from_lengths(cls, edge_ids: Sequence[int], lengths_m: Sequence[float], speed_mps: float) -> Route:
        if len(edge_ids) != len(lengths_m):
            raise ValueError(f"{len(edge_ids)} edges but {len(lengths_m)} lengths")
        return cls(tuple(edge_ids), tuple(m / speed_mps for m in lengths_m))


@dataclass(frozen=True)
class SlowDown:
    """The sensitivity case: an edge whose depth on entry is at least min_depth_cm takes factor times its
    free-flow time. It is a labelled assumption, not a measured speed in water."""

    min_depth_cm: int
    factor: float

    @property
    def label(self) -> str:
        return f"sensitivity: edges at {self.min_depth_cm} cm or deeper take {self.factor:g} times their free-flow time"


@dataclass(frozen=True)
class Violation:
    position: int
    edge_id: int
    arrival_s: float
    step: int
    depth_cm: int


@dataclass(frozen=True)
class Walk:
    departure_s: float
    limit_cm: int
    arrivals_s: tuple[float, ...]
    violations: tuple[Violation, ...]
    beyond_horizon: int
    edges_outside_table: int

    @property
    def violating_edges(self) -> int:
        return len(self.violations)

    @property
    def _worst(self) -> Violation | None:
        return max(self.violations, key=lambda v: v.depth_cm, default=None)

    @property
    def worst_over_limit_cm(self) -> int | None:
        worst = self._worst
        return None if worst is None else worst.depth_cm - self.limit_cm

    @property
    def worst_edge_id(self) -> int | None:
        worst = self._worst
        return None if worst is None else worst.edge_id

    @property
    def first_violation_s(self) -> float | None:
        return self.violations[0].arrival_s - self.departure_s if self.violations else None


def rewalk(
    route: Route,
    departure_s: float,
    step_seconds: Sequence[float],
    depth_cm: DepthLookup,
    limit_cm: int,
    rule: StepRule,
    slowdown: SlowDown | None = None,
) -> Walk:
    """Walk the route from departure_s. depth_cm(edge_id, step) reads the table and raises IndexError for an edge
    outside it. Such an edge is taken as dry and counted, as routing_proof's checker does."""
    time = departure_s
    arrivals, violations = [], []
    beyond = outside = 0
    for position, (edge_id, seconds) in enumerate(zip(route.edge_ids, route.edge_seconds)):
        arrivals.append(time)
        if time > step_seconds[-1]:
            beyond += 1
        read = [(step, _depth(depth_cm, edge_id, step)) for step in steps_for(rule, step_seconds, time)]
        if any(d is None for _, d in read):
            outside += 1
            read = [(step, 0) for step, _ in read]
        step, depth = max(read, key=lambda sd: sd[1])
        if depth >= limit_cm:
            violations.append(Violation(position, edge_id, time, step, depth))
        if slowdown is not None and depth >= slowdown.min_depth_cm:
            seconds *= slowdown.factor
        time += seconds
    return Walk(departure_s, limit_cm, tuple(arrivals), tuple(violations), beyond, outside)


def _depth(lookup: DepthLookup, edge_id: int, step: int) -> int | None:
    try:
        return lookup(edge_id, step)
    except IndexError:
        return None
