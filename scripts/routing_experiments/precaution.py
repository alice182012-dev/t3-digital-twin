"""The two-option plan of decision D-021: a recommended route planned with a precaution depth and a second
option planned with the vehicle's hard limit.

The precaution depth is `fraction * limit`. Both searches use the sticky rule of
scripts/routing_reference/sticky_reference.py. Closed edges at the precaution depth include the closed edges at the
limit, so the recommended route never ends before the limit route. When no route exists under the precaution depth,
the limit route is recommended and flagged as going through water. Pure: no I/O.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

HERE = Path(__file__).resolve().parent
_REFERENCE = str(HERE.parent / "routing_reference")
if _REFERENCE not in sys.path:
    sys.path.insert(0, _REFERENCE)

from sticky_reference import Graph, Route, StickyClosure, earliest_arrival, find_crossings  # noqa: E402

DepthLookup = Callable[[int, int], int]


@dataclass(frozen=True)
class PlanOptions:
    recommended: Route | None
    second: Route | None
    flagged_through_water: bool
    ran_precaution_search: bool


def plan_options(
    graph: Graph,
    origin: int,
    destination: int,
    departure_s: float,
    departure_step_time_s: float,
    step_seconds: Sequence[float],
    depth_cm: DepthLookup,
    limit_cm: int,
    fraction: float,
    margin_s: float,
) -> PlanOptions:
    def closure(limit: float) -> StickyClosure:
        return StickyClosure(tuple(step_seconds), depth_cm, limit, departure_s, margin_s, departure_step_time_s)

    limit_route = earliest_arrival(graph, origin, destination, closure(limit_cm))
    if limit_route is None:
        return PlanOptions(None, None, False, False)
    entries = list(limit_route.arrivals_s) + [limit_route.end_s]
    seconds = [b - a for a, b in zip(entries, entries[1:])]
    precaution = closure(fraction * limit_cm)
    if not find_crossings(limit_route.edge_ids, seconds, precaution):
        return PlanOptions(limit_route, None, False, False)
    precaution_route = earliest_arrival(graph, origin, destination, precaution)
    if precaution_route is None:
        return PlanOptions(limit_route, None, True, True)
    return PlanOptions(precaution_route, limit_route, False, True)
