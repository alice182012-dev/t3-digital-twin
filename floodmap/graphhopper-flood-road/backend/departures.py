"""POST /route/departures: the earliest clear departure of the usual route (US-053).

The usual route is the one GraphHopper returns with no flood model and no time-aware search. The route's `edge_id` and
`time` path details give each edge and when it is entered. For every forecast step from the one that contains now, the
rule of US-050 judges the route: a road is closed for an entry time when a step in [departure, entry + margin] has a depth at
or above the vehicle's limit (scripts/routing_reference/sticky_reference.py is the reference, and a test compares them).

A candidate is `blocked` when any road is closed on entry, else `unknown` when the trip ends after the last forecast step,
else `clear`. The server decides the clock, the margin, and the limit. The client's body carries only the points and the
profile. A missing, damaged, or stale table is an answer with `status: unavailable` and a reason, not an error.

Pure: GraphHopper and the table are passed in, so the flow is tested without a network or a database.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, NamedTuple

import edge_depth_reader as reader

MARGIN_S = 600
PROFILES = ("motorbike", "car", "truck", "foot")
DETAILS = ["edge_id", "time"]
GRAPH_HASH_HINT = "td.graph_hash"


class Outcome(NamedTuple):
    ok: bool
    status: int
    data: Any  # the answer when ok, else the raw GraphHopper error text


def parse_request(body: dict) -> dict:
    """The points and the profile, and nothing else. A clock, a margin, a limit, or a policy from the client is dropped."""
    points = body.get("points")
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError("points needs at least two [lon, lat] points")
    for point in points:
        if not (isinstance(point, (list, tuple)) and len(point) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in point)):
            raise ValueError(f"a point must be [lon, lat], got {point!r}")
    profile = body.get("profile")
    if profile not in PROFILES:
        raise ValueError(f"profile must be one of {', '.join(PROFILES)}")
    return {"points": points, "profile": profile}


def usual_route_body(body: dict) -> dict:
    """The GraphHopper request for the usual route: the details, no flood model, no time-aware search, and `td_info` so the
    answer carries the graph hash that the table is checked against."""
    parsed = parse_request(body)
    return {
        "points": parsed["points"],
        "profile": parsed["profile"],
        "points_encoded": False,
        "details": list(DETAILS),
        "td_info": True,
    }


def entry_offsets(path_details: dict) -> tuple[list[tuple[int, float]], float]:
    """(edge id, seconds from the departure to entering it) for each edge, and the trip time in seconds."""
    edge_ids, times = path_details.get("edge_id"), path_details.get("time")
    if edge_ids is None or times is None:
        raise ValueError("the route has no edge_id and time details")
    if len(edge_ids) != len(times) or any(a[0] != b[0] or a[1] != b[1] for a, b in zip(edge_ids, times)):
        raise ValueError("the edge_id and time details do not line up, so the entry time of an edge is not known")
    edges, elapsed = [], 0.0
    for (_, _, edge_id), (_, _, millis) in zip(edge_ids, times):
        edges.append((int(edge_id), elapsed))
        elapsed += millis / 1000.0
    return edges, elapsed


def _closed(table: reader.Table, steps: list[float], limit_cm: int, edge_id: int, departure: float, entry: float) -> bool:
    if not 0 <= edge_id < table.edge_count:
        return False  # a road outside the model reads as clear
    end = entry + MARGIN_S
    for index, moment in enumerate(steps):
        if moment > end:
            return False
        if moment >= departure and table.depth_cm(edge_id, index) >= limit_cm:
            return True
    return False


def compute(route: dict, table: reader.Table, *, vehicle: str, limit_cm: int, now: datetime) -> dict:
    path = route["paths"][0]
    edges, details_total = entry_offsets(path["details"])
    steps = [t.timestamp() for t in table.step_times]
    last_step = steps[-1]
    now_s = now.timestamp()
    first = max((i for i, s in enumerate(steps) if s <= now_s), default=0)
    trip_s = path.get("time", details_total * 1000) / 1000.0

    candidates = []
    for index in range(first, len(steps)):
        departure = steps[index]
        leave = max(departure, now_s)
        arrival = leave + trip_s
        if any(_closed(table, steps, limit_cm, edge, departure, departure + offset) for edge, offset in edges):
            status = "blocked"
        elif arrival > last_step:
            status = "unknown"
        else:
            status = "clear"
        candidates.append({
            "departure": table.step_times[index].isoformat(),
            "leave_at": datetime.fromtimestamp(leave, timezone.utc).isoformat(),
            "arrival": datetime.fromtimestamp(arrival, timezone.utc).isoformat(),
            "status": status,
        })
    return {
        "status": "ok",
        "run": table.run_name,
        "run_age_s": int(now_s - steps[0]),
        "generated_at": now.isoformat(),
        "vehicle": vehicle,
        "limit_cm": limit_cm,
        "margin_s": MARGIN_S,
        "route": {"distance_m": path.get("distance"), "time_s": trip_s},
        "candidates": candidates,
        "earliest_clear": next((c for c in candidates if c["status"] == "clear"), None),
    }


def unavailable(reason: str, vehicle: str, now: datetime) -> dict:
    return {
        "status": "unavailable",
        "reason": reason,
        "generated_at": now.isoformat(),
        "vehicle": vehicle,
        "margin_s": MARGIN_S,
        "candidates": [],
        "earliest_clear": None,
    }


def departures_request(
    body: dict,
    *,
    post: Callable[[dict], dict],
    load_table: Callable[[], reader.Table],
    limit_for: Callable[[str], int],
    now: datetime,
) -> Outcome:
    """post(body) returns {"ok": True, "status", "json"} or {"ok": False, "status", "error"}. load_table() returns the current
    table or raises TableUnavailable. limit_for(profile) is the depth limit in cm of a vehicle."""
    parsed = parse_request(body)
    response = post(usual_route_body(body))
    if not response.get("ok"):
        return Outcome(False, response.get("status") or 400, response.get("error"))
    route = response["json"]
    vehicle = parsed["profile"]
    try:
        table = load_table()
        loaded_hash = (route.get("hints") or {}).get(GRAPH_HASH_HINT)
        if not loaded_hash:
            raise reader.TableUnavailable("the routing engine did not report its graph hash, so the table cannot be checked")
        reader.require_graph_hash(table, loaded_hash)
    except reader.TableUnavailable as error:
        return Outcome(True, 200, unavailable(str(error), vehicle, now))
    return Outcome(True, 200, compute(route, table, vehicle=vehicle, limit_cm=limit_for(vehicle), now=now))
