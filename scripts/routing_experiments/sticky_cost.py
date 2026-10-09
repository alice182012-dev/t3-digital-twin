"""The cost of sticky closure against an arrival-only reference (US-093).

For one origin, destination, and departure, `compare` plans the sticky route with the reference of
scripts/routing_reference/sticky_reference.py and the arrival-only route of arrival_only.py, and classifies the
pair. The sticky closed set contains the arrival-only closed set, so a sticky route never ends before the
arrival-only route and never exists alone. That holds for a departure at or after the first forecast step, which
`compare` requires. A search that hit its label cap is `INEXACT`, and `summarize` counts those apart. Pure: no I/O.
"""

from __future__ import annotations

import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Hashable, Iterable, Sequence

HERE = Path(__file__).resolve().parent
_REFERENCE = str(HERE.parent / "routing_reference")
if _REFERENCE not in sys.path:
    sys.path.insert(0, _REFERENCE)

from arrival_only import ArrivalOnlyClosure, earliest_arrival_arrival_only  # noqa: E402
from sticky_reference import Graph, StickyClosure, earliest_arrival  # noqa: E402

SAME_TOLERANCE_S = 1e-6


class Outcome(Enum):
    SAME = "same"
    STICKY_LONGER = "sticky_longer"
    STICKY_NO_ROUTE = "sticky_no_route"
    NEITHER_ROUTES = "neither_routes"
    INEXACT = "inexact"


@dataclass(frozen=True)
class CompareRecord:
    outcome: Outcome
    extra_s: float | None  # sticky end minus arrival-only end, set when both routes exist
    exact: bool


def compare(
    graph: Graph,
    origin: int,
    destination: int,
    departure_s: float,
    departure_step_time_s: float,
    step_seconds: Sequence[float],
    depth_cm: Callable[[int, int], int],
    limit_cm: int,
    margin_s: float,
    max_labels_per_node: int = 16,
) -> CompareRecord:
    if departure_s < step_seconds[0]:
        raise ValueError("the departure is before the first forecast step")
    sticky = earliest_arrival(
        graph, origin, destination, StickyClosure(tuple(step_seconds), depth_cm, limit_cm, departure_s, margin_s, departure_step_time_s)
    )
    arrival_only = earliest_arrival_arrival_only(
        graph, origin, destination, ArrivalOnlyClosure(step_seconds, depth_cm, limit_cm), departure_s, max_labels_per_node
    )
    if not arrival_only.exact:
        return CompareRecord(Outcome.INEXACT, None, False)
    if arrival_only.route is None:
        if sticky is not None:
            raise ValueError("sticky found a route that arrival-only cannot: the closed sets are not nested")
        return CompareRecord(Outcome.NEITHER_ROUTES, None, True)
    if sticky is None:
        return CompareRecord(Outcome.STICKY_NO_ROUTE, None, True)
    extra = sticky.end_s - arrival_only.route.end_s
    if extra < -SAME_TOLERANCE_S:
        raise ValueError("sticky ends before arrival-only: the closed sets are not nested")
    return CompareRecord(Outcome.SAME if extra <= SAME_TOLERANCE_S else Outcome.STICKY_LONGER, max(extra, 0.0), True)


@dataclass(frozen=True)
class Distribution:
    n: int
    mean: float
    median: float
    p90: float
    max: float

    @classmethod
    def of(cls, values: Sequence[float]) -> Distribution | None:
        if not values:
            return None
        ordered = sorted(values)
        return cls(len(ordered), statistics.mean(ordered), statistics.median(ordered),
                   ordered[math.ceil(0.9 * len(ordered)) - 1], ordered[-1])


@dataclass(frozen=True)
class Summary:
    """The shares use the exact records as their base. extra_s covers every exact record where both routes
    exist, so cases with no extra time are in it as zeros."""

    n: int
    n_inexact: int
    share_sticky_no_route: float | None
    share_sticky_longer: float | None
    extra_s: Distribution | None


def summarize(records: Iterable[tuple[Hashable, CompareRecord]]) -> dict[Hashable, Summary]:
    groups: dict[Hashable, list[CompareRecord]] = defaultdict(list)
    for key, record in records:
        groups[key].append(record)
    return {key: _summary(group) for key, group in groups.items()}


def _summary(group: list[CompareRecord]) -> Summary:
    exact = [r for r in group if r.exact]

    def share(outcome: Outcome) -> float | None:
        return sum(r.outcome is outcome for r in exact) / len(exact) if exact else None

    return Summary(
        len(group),
        len(group) - len(exact),
        share(Outcome.STICKY_NO_ROUTE),
        share(Outcome.STICKY_LONGER),
        Distribution.of([r.extra_s for r in exact if r.extra_s is not None]),
    )
