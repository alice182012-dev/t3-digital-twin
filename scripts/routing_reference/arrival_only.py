"""Arrival-only closure, the reference the sticky rule is measured against (US-093).

An edge entered at time `a` is closed when its depth at the forecast step at or before `a` reaches the limit.
The step rule is the AT_OR_BEFORE rule of scripts/routing_experiments/rewalk.py, so the search here and the
re-walk read the same step for the same arrival.

This closure is not monotone in `a` and travellers do not wait, so an earlier arrival at a node is not always
better: it can meet a road that a later arrival passes. The search keeps several arrival-time labels per node and
expands them in time order. A cap on the labels per node keeps cyclic graphs finite. A label the cap drops can
only matter when it is earlier than the answer, so the result is exact unless such a label was dropped. A
destination that no road reaches, closed or not, is exact at once. A destination that roads reach but that every
closed-road path misses can exhaust the cap on a cyclic graph, and the result is then inexact.
"""

from __future__ import annotations

import heapq
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

HERE = Path(__file__).resolve().parent
_EXPERIMENTS = str(HERE.parent / "routing_experiments")
if _EXPERIMENTS not in sys.path:
    sys.path.insert(0, _EXPERIMENTS)

from rewalk import StepRule, steps_for  # noqa: E402
from sticky_reference import Graph, Route  # noqa: E402


@dataclass(frozen=True)
class ArrivalOnlyClosure:
    step_seconds: Sequence[float]
    depth_cm: Callable[[int, int], int]
    limit_cm: int

    def is_closed(self, edge_id: int, arrival_s: float) -> bool:
        (step,) = steps_for(StepRule.AT_OR_BEFORE, self.step_seconds, arrival_s)
        return self.depth_cm(edge_id, step) >= self.limit_cm


@dataclass(frozen=True)
class ArrivalOnlyResult:
    route: Route | None
    exact: bool


@dataclass(frozen=True)
class _Label:
    time: float
    node: int
    parent: _Label | None
    edge_id: int | None


def earliest_arrival_arrival_only(
    graph: Graph,
    origin: int,
    destination: int,
    rule: ArrivalOnlyClosure,
    departure_s: float,
    max_labels_per_node: int = 16,
) -> ArrivalOnlyResult:
    if destination not in _reachable(graph, origin):
        return ArrivalOnlyResult(None, exact=True)
    start = _Label(departure_s, origin, None, None)
    queue: list[tuple[float, int, int, _Label]] = [(departure_s, origin, 0, start)]
    seen: dict[int, set[float]] = {origin: {departure_s}}
    earliest_dropped = float("inf")
    pushed = 0
    found: _Label | None = None
    while queue:
        _, _, _, label = heapq.heappop(queue)
        if label.node == destination:
            found = label
            break
        for edge in graph.out_edges(label.node):
            if rule.is_closed(edge.id, label.time):
                continue
            arrival = label.time + edge.seconds
            times = seen.setdefault(edge.head, set())
            if arrival in times:
                continue
            if len(times) >= max_labels_per_node:
                earliest_dropped = min(earliest_dropped, arrival)
                continue
            times.add(arrival)
            pushed += 1
            heapq.heappush(queue, (arrival, edge.head, pushed, _Label(arrival, edge.head, label, edge.id)))
    end = float("inf") if found is None else found.time
    exact = earliest_dropped >= end
    return ArrivalOnlyResult(None if found is None else _route(found), exact)


def _reachable(graph: Graph, origin: int) -> set[int]:
    reached, stack = {origin}, [origin]
    while stack:
        for edge in graph.out_edges(stack.pop()):
            if edge.head not in reached:
                reached.add(edge.head)
                stack.append(edge.head)
    return reached


def _route(label: _Label) -> Route:
    edge_ids: list[int] = []
    entered: list[float] = []
    end = label.time
    while label.parent is not None:
        edge_ids.append(label.edge_id)
        entered.append(label.parent.time)
        label = label.parent
    edge_ids.reverse()
    entered.reverse()
    return Route(tuple(edge_ids), tuple(entered), end)
