"""Arrival-only closure, the reference the sticky rule is measured against (US-093, BL-027 option A).

An edge entered at time `a` is closed when its depth at the forecast step at or before `a` reaches the limit.
The step rule is the AT_OR_BEFORE rule of scripts/routing_experiments/rewalk.py, so the search here and the
re-walk read the same step for the same arrival.

The reference is the earliest arrival over routes that visit no node twice. The traveller does not wait and does
not loop, and the departure time is fixed. The closure is not monotone in `a` (a road closed at one arrival can be
open at a later one), so the search keeps a label for every simple path and orders them by arrival time plus a
lower bound on the time left. The first destination label popped is the optimum, and no label is merged or
dropped, so the result is exact unless the expansion budget runs out first.

Two bounds come from a relaxation that lets the traveller wait at any node and walk any walk. Every route the
search accepts is also a route of the relaxation, so the relaxation never rules out a real route.

- latest[v] is the latest time a traveller can be at v and still reach the destination in the relaxation. A label
  that arrives at v later than latest[v] cannot reach the destination, so the search drops it. This ends a search
  whose destination every closed road shuts off. Without it the search enumerates every simple path.
- The time left is the shortest travel time to the destination over the roads that are open at some step from the
  departure on. A road that is closed at every such step is never usable and is left out.
"""

from __future__ import annotations

import bisect
import functools
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

DEFAULT_MAX_EXPANSIONS = 1_000_000
_EPS = 1e-9
_INF = float("inf")


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
    """lower_bound_s is set when the search ran out of budget. No route can end before it: the smallest bound of
    any label still in the queue is at most the end of every route the search has not reached."""

    route: Route | None
    exact: bool
    lower_bound_s: float | None = None


@dataclass(frozen=True)
class _Label:
    time: float
    node: int
    parent: _Label | None
    edge_id: int | None


class SimplePathSearch:
    """Builds the reverse arcs of a graph once and answers any number of searches on it."""

    def __init__(self, graph: Graph) -> None:
        self._graph = graph
        nodes = {e.tail for e in graph.edges()} | {e.head for e in graph.edges()}
        self._into: dict[int, list[tuple[int, int, float]]] = {}
        for tail in nodes:
            for edge in graph.out_edges(tail):
                self._into.setdefault(edge.head, []).append((tail, edge.id, edge.seconds))

    def earliest_arrival(
        self,
        origin: int,
        destination: int,
        rule: ArrivalOnlyClosure,
        departure_s: float,
        max_expansions: int = DEFAULT_MAX_EXPANSIONS,
    ) -> tuple[ArrivalOnlyResult, int]:
        """The result and the number of label expansions used."""
        latest = self._latest_feasible(destination, rule, departure_s)
        if origin not in latest:
            return ArrivalOnlyResult(None, exact=True), 0
        bound = self._seconds_to(destination, rule, departure_s, latest)
        if origin not in bound:
            return ArrivalOnlyResult(None, exact=True), 0
        queue: list[tuple[float, float, int, _Label]] = [
            (departure_s + bound[origin], departure_s, 0, _Label(departure_s, origin, None, None))
        ]
        pushed = 0
        expansions = 0
        while queue:
            bound_s, _, _, label = heapq.heappop(queue)
            if label.node == destination:
                return ArrivalOnlyResult(_route(label), exact=True), expansions
            if expansions >= max_expansions:
                return ArrivalOnlyResult(None, exact=False, lower_bound_s=bound_s), expansions
            expansions += 1
            for edge in self._graph.out_edges(label.node):
                head = edge.head
                if head not in bound or _on_chain(label, head) or rule.is_closed(edge.id, label.time):
                    continue
                arrival = label.time + edge.seconds
                if arrival > latest[head] + _EPS:
                    continue
                pushed += 1
                heapq.heappush(queue, (arrival + bound[head], arrival, pushed, _Label(arrival, head, label, edge.id)))
        return ArrivalOnlyResult(None, exact=True), expansions

    def _latest_feasible(self, destination: int, rule: ArrivalOnlyClosure, departure_s: float) -> dict[int, float]:
        """latest[v] for every node whose latest time is at least the departure. The destination has no limit."""
        latest = {destination: _INF}
        queue = [(-_INF, destination)]
        while queue:
            negated, node = heapq.heappop(queue)
            bound = -negated
            if bound < latest[node]:
                continue
            if bound < departure_s:
                break
            for tail, edge_id, seconds in self._into.get(node, ()):
                open_until = _latest_open(rule, edge_id, bound - seconds)
                if open_until is not None and open_until >= departure_s and open_until > latest.get(tail, -_INF):
                    latest[tail] = open_until
                    heapq.heappush(queue, (-open_until, tail))
        return {node: bound for node, bound in latest.items() if bound >= departure_s}

    def _seconds_to(
        self, destination: int, rule: ArrivalOnlyClosure, departure_s: float, latest: dict[int, float]
    ) -> dict[int, float]:
        """Shortest travel time to the destination over roads that are open at some step from the departure on,
        among the nodes of latest. Nodes missing from the result cannot reach the destination."""
        first = _step(rule, departure_s)
        best = {destination: 0.0}
        queue = [(0.0, destination)]
        while queue:
            seconds, node = heapq.heappop(queue)
            if seconds > best[node]:
                continue
            for tail, edge_id, edge_seconds in self._into.get(node, ()):
                if tail not in latest or not _ever_open(rule, edge_id, first):
                    continue
                candidate = seconds + edge_seconds
                if candidate < best.get(tail, _INF):
                    best[tail] = candidate
                    heapq.heappush(queue, (candidate, tail))
        return best


def earliest_arrival_arrival_only(
    graph: Graph,
    origin: int,
    destination: int,
    rule: ArrivalOnlyClosure,
    departure_s: float,
    max_expansions: int = DEFAULT_MAX_EXPANSIONS,
) -> ArrivalOnlyResult:
    return _search_for(graph).earliest_arrival(origin, destination, rule, departure_s, max_expansions)[0]


@functools.lru_cache(maxsize=2)
def _search_for(graph: Graph) -> SimplePathSearch:
    """One reverse index per graph, so repeated calls on the same graph do not rebuild it. A Graph does not
    change after it is built, and the cache keys on the object, not its contents."""
    return SimplePathSearch(graph)


def _step(rule: ArrivalOnlyClosure, time_s: float) -> int:
    """The step the closure reads at a time: the step at or before it, the first step before the first."""
    if time_s == _INF:
        return len(rule.step_seconds) - 1
    return max(bisect.bisect_right(rule.step_seconds, time_s) - 1, 0)


def _open_at(rule: ArrivalOnlyClosure, edge_id: int, step: int) -> bool:
    return rule.depth_cm(edge_id, step) < rule.limit_cm


def _ever_open(rule: ArrivalOnlyClosure, edge_id: int, first_step: int) -> bool:
    return any(_open_at(rule, edge_id, k) for k in range(first_step, len(rule.step_seconds)))


def _latest_open(rule: ArrivalOnlyClosure, edge_id: int, at_most_s: float) -> float | None:
    """The latest time up to at_most_s at which the road is open, or the end of its latest open step when the
    road is closed at at_most_s. None when the road is closed at every step up to at_most_s. The end of a step
    is not itself open, so the value can overstate by one instant, which keeps the bound safe."""
    step = _step(rule, at_most_s)
    if _open_at(rule, edge_id, step):
        return at_most_s
    for earlier in range(step - 1, -1, -1):
        if _open_at(rule, edge_id, earlier):
            return rule.step_seconds[earlier + 1]
    return None


def _on_chain(label: _Label | None, node: int) -> bool:
    while label is not None:
        if label.node == node:
            return True
        label = label.parent
    return False


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
