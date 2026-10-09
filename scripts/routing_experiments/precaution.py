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
from typing import Callable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
_REFERENCE = str(HERE.parent / "routing_reference")
if _REFERENCE not in sys.path:
    sys.path.insert(0, _REFERENCE)

from sticky_cost import Distribution  # noqa: E402
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


@dataclass(frozen=True)
class FractionRow:
    """Shares are None when no pair has a route under the limit. extra_s is the recommended route's end minus the
    limit route's end over every routed pair, so pairs with the same route are in it as zeros."""

    n_routed: int
    n_no_route: int  # pairs with no route under the limit, left out of every share
    share_recommended_under_precaution: float | None
    share_flagged: float | None
    share_single_option: float | None
    share_search_skipped: float | None
    extra_s: Distribution | None


def sweep_fraction(
    graph: Graph,
    pairs: Sequence[tuple[int, int]],
    departure_s: float,
    departure_step_time_s: float,
    step_seconds: Sequence[float],
    depth_cm: DepthLookup,
    margin_s: float,
    limits: Mapping[str, int],
    fractions: Sequence[float],
) -> dict[tuple[str, float], FractionRow]:
    out = {}
    for vehicle, limit_cm in limits.items():
        for fraction in fractions:
            options = [
                plan_options(graph, o, d, departure_s, departure_step_time_s, step_seconds, depth_cm, limit_cm, fraction, margin_s)
                for o, d in pairs
            ]
            routed = [x for x in options if x.recommended is not None]
            out[(vehicle, fraction)] = _row(routed, len(options) - len(routed))
    return out


def _row(routed: list[PlanOptions], n_no_route: int) -> FractionRow:
    n = len(routed)

    def share(count: int) -> float | None:
        return count / n if n else None

    extra = [x.recommended.end_s - x.second.end_s if x.second else 0.0 for x in routed]
    return FractionRow(
        n,
        n_no_route,
        share(sum(not x.flagged_through_water for x in routed)),
        share(sum(x.flagged_through_water for x in routed)),
        share(sum(x.second is None for x in routed)),
        share(sum(not x.ran_precaution_search for x in routed)),
        Distribution.of(extra),
    )
