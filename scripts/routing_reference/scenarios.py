"""The four synthetic flood scenarios of routing-not-time-aware.md, run through the offline reference.

Story R2 (US-047). Each scenario floods one road of a real route and asks whether a traveller who
reaches it at a fixed minute may enter. The expected result is the "C-lite, sticky" column of the
blocker's test table. A scenario sets the traveller's speed so the corridor road is entered at exactly
the table's minute, because the table fixes the minute and not the distance.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from corridor import RoadNetwork
from sticky_reference import DEFAULT_MARGIN_S, Crossing, Edge, Graph, Route, StickyClosure, earliest_arrival, find_crossings

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "floodmap" / "graphhopper-flood-road" / "scripts"))
from flood_utils import VEHICLE_PROFILES  # noqa: E402

STEP_MINUTES = 15
STEP_COUNT = 8  # the 8 steps of a real run, 15 minutes apart, 105 minutes from the first to the last
STEP_SECONDS = tuple(60 * STEP_MINUTES * k for k in range(STEP_COUNT))

VEHICLE_LIMIT_CM = {vehicle: VEHICLE_PROFILES[vehicle]["threshold_cm"] for vehicle in ("motorbike", "car")}

DEFAULT_FLOOD_CM = 50
_CORRIDOR_AT = {"middle": 0.5, "far": 0.9}  # how far along the route the corridor road is entered


@dataclass(frozen=True)
class Scenario:
    name: str
    corridor: Literal["middle", "far"]
    arrival_min: int
    flooded: tuple[tuple[int, int | None], ...]  # (first minute, last minute or None), inclusive
    blocked: bool  # the sticky column's result: may the traveller not enter the corridor road?


SCENARIOS = (
    Scenario("1. Rises before arrival", "middle", 15, ((10, None),), blocked=True),
    Scenario("2. Rises after passing", "middle", 15, ((45, None),), blocked=False),
    Scenario("3. Flooded and drains", "middle", 25, ((0, 20),), blocked=True),
    Scenario("4. Far road floods late", "far", 30, ((45, None),), blocked=False),
)


def scenario_depth_cm(scenario: Scenario, step: int, flood_cm: int = DEFAULT_FLOOD_CM) -> int:
    minute = step * STEP_MINUTES
    flooded = any(first <= minute and (last is None or minute <= last) for first, last in scenario.flooded)
    return flood_cm if flooded else 0


@dataclass(frozen=True)
class Outcome:
    scenario: Scenario
    with_detour: bool
    route: Route | None
    uses_corridor: bool
    crossings: list[Crossing]  # of the returned route. Always empty when the reference is right.
    static_crossings: list[Crossing]  # of the plain shortest route, which ignores time
    corridor_arrival_s: float
    corridor_position: float  # 0 at the origin, 1 at the destination
    corridor_way_id: str
    path_edges: int  # edges of the plain shortest route
    path_length_m: float

    @property
    def observed(self) -> Literal["corridor", "detour", "none"]:
        if self.route is None:
            return "none"
        return "corridor" if self.uses_corridor else "detour"

    @property
    def expected(self) -> Literal["corridor", "detour", "none"]:
        if not self.scenario.blocked:
            return "corridor"
        return "detour" if self.with_detour else "none"

    @property
    def matches_sticky_column(self) -> bool:
        return self.observed == self.expected and not self.crossings


def run_scenario(
    network: RoadNetwork,
    origin: int,
    destination: int,
    scenario: Scenario,
    limit_cm: int,
    with_detour: bool,
    flood_cm: int = DEFAULT_FLOOD_CM,
) -> Outcome:
    path = network.shortest_path_edges(origin, destination)
    if path is None:
        raise ValueError("no route between the origin and the destination")
    if len(path) < 3:
        raise ValueError(f"the route has {len(path)} edges, a scenario needs at least 3 edges")
    lengths = [network.edges[e].length_m for e in path]
    entered_at = [sum(lengths[:i]) for i in range(len(path))]
    total = sum(lengths)
    index = max(i for i in range(1, len(path)) if entered_at[i] <= _CORRIDOR_AT[scenario.corridor] * total)
    corridor, opposite = path[index], path[index] ^ 1

    speed_mps = entered_at[index] / (scenario.arrival_min * 60)
    edge_ids = set(path)
    if with_detour:
        detour = network.shortest_path_edges(origin, destination, banned=frozenset({corridor, opposite}))
        if detour is None:
            raise ValueError("the network has no detour around the corridor road")
        edge_ids |= set(detour)
    graph = Graph(Edge(e, network.edges[e].tail, network.edges[e].head, network.edges[e].length_m / speed_mps) for e in sorted(edge_ids))

    rule = StickyClosure(
        STEP_SECONDS,
        lambda edge_id, step: scenario_depth_cm(scenario, step, flood_cm) if edge_id in (corridor, opposite) else 0,
        limit_cm,
        departure_s=0,
        margin_s=DEFAULT_MARGIN_S,
    )
    route = earliest_arrival(graph, origin, destination, rule)
    crossings = find_crossings(route.edge_ids, [graph.edge(e).seconds for e in route.edge_ids], rule) if route else []
    static = find_crossings(path, [graph.edge(e).seconds for e in path], rule)
    return Outcome(
        scenario,
        with_detour,
        route,
        route is not None and corridor in route.edge_ids,
        crossings,
        static,
        corridor_arrival_s=entered_at[index] / speed_mps,
        corridor_position=entered_at[index] / total,
        corridor_way_id=network.edges[corridor].way_id,
        path_edges=len(path),
        path_length_m=total,
    )
