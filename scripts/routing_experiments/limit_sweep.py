"""The vehicle-limit sweep of the single-timestep model (US-092), offline on the Python reference.

Each plan limit closes the edges whose depth at the departure step reaches it, plans the shortest route over the
rest, and is judged by the at-or-before step rule of rewalk.py at one or more judge limits. The regret table is the
violation rate for every plan limit against every judge limit.

The cost-band sweep (the start of the band at 25, 50, and 75 percent of the limit) is not built, because the
reference has no cost factors and this module does not invent them.

Pure: no I/O. The edge depth is a callable, so a real table can be wrapped later.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable, Hashable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
_REFERENCE = str(HERE.parent / "routing_reference")
if _REFERENCE not in sys.path:
    sys.path.insert(0, _REFERENCE)

from rewalk import Route as WalkRoute  # noqa: E402
from rewalk import StepRule, Violation, rewalk  # noqa: E402
from sticky_reference import Graph, Route, StickyClosure, earliest_arrival  # noqa: E402

NEVER_CLOSED = sys.maxsize

DepthLookup = Callable[[int, int], int]


def plan_single_timestep(
    graph: Graph,
    origin: int,
    destination: int,
    departure_s: float,
    depth_at_departure_step: Callable[[int], int],
    limit: int,
) -> Route | None:
    """The shortest route over the edges whose depth at the departure step is below the limit (the US-091
    single-timestep model). The closure is static, so the sticky search with one step and no margin is a plain
    Dijkstra."""
    static = StickyClosure((departure_s,), lambda edge_id, _step: depth_at_departure_step(edge_id), limit, departure_s, 0)
    return earliest_arrival(graph, origin, destination, static)


def judge(
    route: Route, departure_s: float, step_seconds: Sequence[float], depth_cm: DepthLookup, judge_limit: int
) -> tuple[Violation, ...]:
    """The edges the route enters at a depth that reaches judge_limit, reading the step at or before each entry."""
    entries = list(route.arrivals_s) + [route.end_s]
    seconds = tuple(b - a for a, b in zip(entries, entries[1:]))
    walk = rewalk(WalkRoute(route.edge_ids, seconds), departure_s, step_seconds, depth_cm, judge_limit, StepRule.AT_OR_BEFORE)
    return walk.violations


@dataclass(frozen=True)
class PlanRow:
    """Rates are None when no pair has a route at this limit. mean_detour_s is the extra travel time over the
    unflooded shortest route, over the pairs that have a route."""

    plan_limit: int
    closed_km: float
    route_share: float
    mean_detour_s: float | None
    violation_rate: float | None  # judged at the plan limit itself


@dataclass(frozen=True)
class SweepResult:
    rows: tuple[PlanRow, ...]
    regret: Mapping[tuple[int, int], float | None]  # (plan limit, judge limit) -> violation rate
    n_pairs: int  # pairs with an unflooded route, the base of every share
    n_dry_unreachable: int  # pairs left out because no road connects them even when dry


def sweep(
    graph: Graph,
    pairs: Sequence[tuple[int, int]],
    departure_s: float,
    departure_step: int,
    step_seconds: Sequence[float],
    depth_cm: DepthLookup,
    length_m: Callable[[int], float],
    plan_limits: Sequence[int],
    judge_limits: Sequence[int],
    road_key: Callable[[int], Hashable] | None = None,
) -> SweepResult:
    """Closed length is summed once per edge. When road_key maps the two directions of a road to one key, it is
    summed once per road, with the length of the first closed edge of that road."""

    def at_departure(edge_id: int) -> int:
        return depth_cm(edge_id, departure_step)

    dry = {}
    for pair in pairs:
        route = plan_single_timestep(graph, *pair, departure_s, at_departure, NEVER_CLOSED)
        if route is not None:
            dry[pair] = route
    rows, regret = [], {}
    for plan_limit in plan_limits:
        planned = {}
        for pair in dry:
            route = plan_single_timestep(graph, *pair, departure_s, at_departure, plan_limit)
            if route is not None:
                planned[pair] = route
        closed = [e.id for e in graph.edges() if at_departure(e.id) >= plan_limit]
        detours = [planned[p].end_s - dry[p].end_s for p in planned]
        for judge_limit in judge_limits:
            regret[(plan_limit, judge_limit)] = _violation_rate(planned.values(), departure_s, step_seconds, depth_cm, judge_limit)
        rows.append(
            PlanRow(
                plan_limit,
                _closed_km(closed, length_m, road_key),
                len(planned) / len(dry) if dry else 0.0,
                mean(detours) if detours else None,
                _violation_rate(planned.values(), departure_s, step_seconds, depth_cm, plan_limit),
            )
        )
    return SweepResult(tuple(rows), regret, len(dry), len(pairs) - len(dry))


def _closed_km(closed: Sequence[int], length_m: Callable[[int], float], road_key: Callable[[int], Hashable] | None) -> float:
    if road_key is None:
        return sum(length_m(e) for e in closed) / 1000
    by_road: dict[Hashable, float] = {}
    for e in closed:
        by_road.setdefault(road_key(e), length_m(e))
    return sum(by_road.values()) / 1000


def _violation_rate(routes, departure_s, step_seconds, depth_cm, judge_limit) -> float | None:
    routes = list(routes)
    if not routes:
        return None
    return sum(bool(judge(r, departure_s, step_seconds, depth_cm, judge_limit)) for r in routes) / len(routes)


@dataclass(frozen=True)
class Conclusion:
    """What a sweep says: which plan limits leave a violation rate above zero, and the plan limits ordered by
    route share, highest first. Equal shares are ordered by the lower limit first."""

    violating_limits: frozenset[int]
    share_rank: tuple[int, ...]

    @classmethod
    def of(cls, result: SweepResult) -> Conclusion:
        violating = frozenset(r.plan_limit for r in result.rows if r.violation_rate)
        rank = tuple(r.plan_limit for r in sorted(result.rows, key=lambda r: (-r.route_share, r.plan_limit)))
        return cls(violating, rank)


@dataclass(frozen=True)
class Change:
    setting: Hashable
    violations_changed: bool
    rank_changed: bool


def conclusion_changes(results: Mapping[Hashable, SweepResult], baseline: Hashable) -> list[Change]:
    """The settings (a vehicle, a storm stage, a departure step, as the caller labels them) whose conclusion
    differs from the baseline's, in the order of `results`. Every setting must sweep the same plan limits."""
    base_limits = {r.plan_limit for r in results[baseline].rows}
    base = Conclusion.of(results[baseline])
    changes = []
    for setting, result in results.items():
        if setting == baseline:
            continue
        if {r.plan_limit for r in result.rows} != base_limits:
            raise ValueError(f"setting {setting!r} sweeps different plan limits than the baseline")
        conclusion = Conclusion.of(result)
        change = Change(setting, conclusion.violating_limits != base.violating_limits, conclusion.share_rank != base.share_rank)
        if change.violations_changed or change.rank_changed:
            changes.append(change)
    return changes
