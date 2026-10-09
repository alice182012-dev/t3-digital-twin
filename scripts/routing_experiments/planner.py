"""The call that plans a route for the routing experiments (US-091).

A planner is any function from a PlanRequest to a PlannedRoute or a PlanFailure, so a test passes a fake one and
the server run passes http_planner. Whether the backend plans with the single-timestep model or the sticky engine
is the backend's TIME_AWARE_ROUTING flag, not a request field, so the caller labels the run with the model it set.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Union

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend_soak"))

from rewalk import Route  # noqa: E402
from sampling import Pair  # noqa: E402

ENGINE_HINTS = ("td.status", "td.run", "td.departure")


@dataclass(frozen=True)
class PlanRequest:
    pair: Pair
    vehicle: str
    valid_time: str  # the departure step, ISO 8601, as /flood/timesteps lists it
    run: str


@dataclass(frozen=True)
class PlannedRoute:
    route: Route
    edge_lengths_m: tuple[float, ...]
    distance_m: float
    engine: dict  # td.* hints without the prefix; empty when the engine did not run


@dataclass(frozen=True)
class PlanFailure:
    status: int
    message: str

    @property
    def cannot_find_point(self) -> bool:
        return "Cannot find point" in self.message


Planner = Callable[[PlanRequest], Union[PlannedRoute, PlanFailure]]


def route_body(request: PlanRequest) -> dict:
    return {"points": [list(request.pair.origin), list(request.pair.destination)], "profile": request.vehicle,
            "points_encoded": False, "instructions": False, "details": ["edge_id", "time", "distance"],
            "valid_time": request.valid_time, "run": request.run}


def _per_edge(edge_intervals: list, intervals: list) -> list[float]:
    """GraphHopper path details are [from point, to point, value] intervals, and two details need not cut the path
    at the same points. Sum the values that fall inside each edge's interval."""
    out = []
    for start, end, _ in edge_intervals:
        out.append(sum(value for a, b, value in intervals if start <= a and b <= end))
    return out


def parse_route_response(status: int, payload: dict) -> PlannedRoute | PlanFailure:
    if status != 200:
        return PlanFailure(status, payload.get("message") or payload.get("error") or "")
    path = payload["paths"][0]
    details = path.get("details") or {}
    edges = details.get("edge_id") or []
    if not edges:
        return PlanFailure(status, "the route has no edge_id detail")
    seconds = [ms / 1000.0 for ms in _per_edge(edges, details.get("time") or [])]
    lengths = _per_edge(edges, details.get("distance") or [])
    hints = payload.get("hints") or {}
    engine = {key.split(".", 1)[1]: hints[key] for key in ENGINE_HINTS if key in hints}
    return PlannedRoute(Route(tuple(e[2] for e in edges), tuple(seconds)), tuple(lengths), path.get("distance"), engine)


def http_planner(backend: str, post=None) -> Planner:
    if post is None:
        from soak_checks import post_json as post

    def plan(request: PlanRequest) -> PlannedRoute | PlanFailure:
        status, payload, _ = post(f"{backend}/route", route_body(request))
        return parse_route_response(status, payload)

    return plan
