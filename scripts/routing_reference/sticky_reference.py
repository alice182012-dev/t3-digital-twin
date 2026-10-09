"""Offline reference for sticky C-lite routing, and a checker for routes it or GraphHopper returns.

Story R2 (US-047) of artifacts/docs/user-stories/time-aware-routing-engine-stories.md. The closure rule
is the one in artifacts/docs/prds/time-aware-routing-engine.md, goal 1: an edge is impassable for a
traveller who enters it at time `a` when its depth reaches the vehicle's limit at any forecast step in
[departure, a + margin]. Closures only grow with `a`, so an earlier arrival is never worse and a plain
Dijkstra over arrival times is exact. Edge ids are the ids of the GraphHopper edge_id path detail and
the rows of the edge depth table (scripts/edge_depth/edge_depth_table.py).

The search ranks routes by travel time. The engine's depth-band cost factors are left out on purpose, so
the reference answers one question: which routes are allowed, and which allowed route arrives first.
Pure: no database, no I/O. Slow on purpose, so it is easy to read.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

DEFAULT_MARGIN_S = 600


@dataclass(frozen=True)
class Edge:
    id: int
    tail: int
    head: int
    seconds: float

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError(f"edge {self.id} has a negative travel time")


class Graph:
    def __init__(self, edges: Iterable[Edge]) -> None:
        self._edges: dict[int, Edge] = {}
        self._out: dict[int, list[Edge]] = {}
        for e in edges:
            if e.id in self._edges:
                raise ValueError(f"edge id {e.id} appears twice")
            self._edges[e.id] = e
            self._out.setdefault(e.tail, []).append(e)

    def edge(self, edge_id: int) -> Edge:
        return self._edges[edge_id]

    def out_edges(self, node: int) -> list[Edge]:
        return self._out.get(node, [])


@dataclass(frozen=True)
class StickyClosure:
    """step_seconds are the forecast step times in seconds from one fixed origin, the same origin as
    departure_s and every arrival. depth_cm(edge_id, step) is the depth of an edge at a step index.

    departure_s starts the clock of the trip. window_start_s starts the window of steps and defaults to
    departure_s. The engine sets it to the step that contains the departure (US-096), so that step counts
    while every arrival is still measured from the real departure."""

    step_seconds: tuple[float, ...]
    depth_cm: Callable[[int, int], int]
    limit_cm: int
    departure_s: float = 0
    margin_s: float = DEFAULT_MARGIN_S
    window_start_s: float | None = None

    def __post_init__(self) -> None:
        if any(b <= a for a, b in zip(self.step_seconds, self.step_seconds[1:])):
            raise ValueError("step times must be strictly increasing")
        if self.margin_s < 0:
            raise ValueError("the margin cannot be negative")

    @property
    def window_start(self) -> float:
        return self.departure_s if self.window_start_s is None else self.window_start_s

    def closing_step(self, edge_id: int, arrival_s: float) -> int | None:
        """The first step in the window [window start, arrival + margin] whose depth reaches the limit."""
        end = arrival_s + self.margin_s
        for step, t in enumerate(self.step_seconds):
            if t > end:
                return None
            if t >= self.window_start and self.depth_cm(edge_id, step) >= self.limit_cm:
                return step
        return None

    def is_closed(self, edge_id: int, arrival_s: float) -> bool:
        return self.closing_step(edge_id, arrival_s) is not None


@dataclass(frozen=True)
class Route:
    edge_ids: tuple[int, ...]
    arrivals_s: tuple[float, ...]  # when the traveller enters each edge
    end_s: float


def earliest_arrival(graph: Graph, origin: int, destination: int, rule: StickyClosure) -> Route | None:
    """The route that reaches the destination first without entering a closed edge, or None."""
    best: dict[int, float] = {origin: rule.departure_s}
    via: dict[int, tuple[int, int, float]] = {}  # node -> (previous node, edge id, entry time)
    queue: list[tuple[float, int]] = [(rule.departure_s, origin)]
    while queue:
        time, node = heapq.heappop(queue)
        if time > best[node]:
            continue
        if node == destination:
            break
        for edge in graph.out_edges(node):
            if rule.is_closed(edge.id, time):
                continue
            arrival = time + edge.seconds
            if arrival < best.get(edge.head, float("inf")):
                best[edge.head] = arrival
                via[edge.head] = (node, edge.id, time)
                heapq.heappush(queue, (arrival, edge.head))
    if destination not in best:
        return None
    path: list[tuple[int, float]] = []
    node = destination
    while node != origin:
        previous, edge_id, entered = via[node]
        path.append((edge_id, entered))
        node = previous
    path.reverse()
    return Route(tuple(e for e, _ in path), tuple(t for _, t in path), best[destination])


@dataclass(frozen=True)
class Crossing:
    position: int  # index of the edge in the route
    edge_id: int
    arrival_s: float
    closing_step: int


def find_crossings(
    edge_ids: Sequence[int], edge_seconds: Sequence[float], rule: StickyClosure
) -> list[Crossing]:
    """Walk a route edge by edge from the departure time and list every edge that was closed on entry.

    edge_seconds holds the travel time of each edge, in the order of edge_ids. For a GraphHopper route,
    these are the `time` path detail (milliseconds, so divide by 1000) next to the `edge_id` detail.
    """
    if len(edge_ids) != len(edge_seconds):
        raise ValueError(f"{len(edge_ids)} edges but {len(edge_seconds)} travel times")
    crossings = []
    time = rule.departure_s
    for position, (edge_id, seconds) in enumerate(zip(edge_ids, edge_seconds)):
        step = rule.closing_step(edge_id, time)
        if step is not None:
            crossings.append(Crossing(position, edge_id, time, step))
        time += seconds
    return crossings
