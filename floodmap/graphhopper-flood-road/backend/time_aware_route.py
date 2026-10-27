"""The request flow of POST /route with the time-aware engine behind a flag (US-052).

Pure: GraphHopper and the flood areas are passed in, so the flow is tested without a network or a database.

Flag off (the default): the request goes as it did before this story.

Flag on: the backend sends `td_departure`, the later of the request's `valid_time` and the server clock, as epoch
seconds, and no flood custom_model, because the engine judges every road over the trip. The engine floors the departure to
the forecast step that contains it. GraphHopper answers with the hints `td.status` (`applied`, `unknown`, or `fallback`),
`td.run`, and for a fallback `td.reason`. On `fallback`, or when the answer carries no `td.status` (a GraphHopper
that does not run the engine), the backend sends today's request, with the custom_model of the flood areas, and keeps
`td.status: fallback` and the reason in the response, so a missing, stale, or mismatched table gives today's behavior and
says so. An error answer passes through unchanged: when the table closes every route GraphHopper says "Connection not
found", which is what the client's departure advice reacts to.

The client never picks the departure, the margin, the limit, or the precaution fraction. Its `td_*` fields are removed.

An applied answer can carry two paths (D-021): path 0 is the recommended route under the precaution depth and path 1 is
the limit route. The hints `td.kinds` (one kind per path, `recommended` or `through_water`), `td.limit_cm`, and
`td.precaution_cm` come with them. The answer passes through as it is, so the order and the hints reach the client.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, NamedTuple

FLAG = "TIME_AWARE_ROUTING"
STATUS_HINT = "td.status"
REASON_HINT = "td.reason"
CLIENT_TD_FIELDS = ("td_departure", "td_limit_cm", "td_precaution_fraction")
FLOOD_FIELDS = ("valid_time", "run", "vehicle_type", "buffer", "simplify", "min_area")
NO_ENGINE_REASON = "the routing engine did not report time-aware routing (GraphHopper without the time-aware module)"


class Outcome(NamedTuple):
    ok: bool
    status: int
    data: Any  # the GraphHopper JSON when ok, else the raw error text


def flag_enabled(env: Mapping[str, str]) -> bool:
    return env.get(FLAG, "").strip().lower() in ("1", "true", "yes", "on")


def departure_epoch(valid_time: str | None, now: datetime) -> int:
    """The later of valid_time and now, in whole epoch seconds. A traveller cannot leave in the past."""
    moment = now
    if valid_time:
        try:
            parsed = datetime.fromisoformat(str(valid_time).replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"valid_time is not an ISO time: {valid_time!r}") from error
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        moment = max(parsed, now)
    return int(moment.timestamp())


def route_request(
    body: dict,
    *,
    post: Callable[[dict], dict],
    custom_model: Callable[..., dict | None],
    enabled: bool,
    now: datetime,
    defaults: tuple = (None, None, None),
) -> Outcome:
    """post(body) returns {"ok": True, "status", "json"} or {"ok": False, "status", "error"}.
    custom_model(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2) returns the flood custom_model, or None
    when no area is flooded."""
    body = dict(body)
    for field in CLIENT_TD_FIELDS:
        body.pop(field, None)
    valid_time = body.pop("valid_time", None)
    run = body.pop("run", "latest")
    vehicle_type = body.pop("vehicle_type", None) or body.get("profile", "motorbike")
    flood = [body.pop(name, None) for name in ("buffer", "simplify", "min_area")]
    buffer_m, simplify_m, min_area_m2 = (float(v) if v is not None else d for v, d in zip(flood, defaults))

    def todays_body() -> dict:
        out = copy.deepcopy(body)
        if valid_time:
            model = custom_model(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)
            if model:
                out["ch.disable"] = True
                out["custom_model"] = model
        return out

    if not enabled:
        return _outcome(post(todays_body()))

    first_body = copy.deepcopy(body)
    first_body["td_departure"] = departure_epoch(valid_time, now)
    first = post(first_body)
    if not first.get("ok"):
        return _outcome(first)
    hints = first["json"].get("hints") or {}
    status = hints.get(STATUS_HINT)
    if status in ("applied", "unknown"):
        return _outcome(first)

    reason = hints.get(REASON_HINT) or NO_ENGINE_REASON
    second = post(todays_body())
    if not second.get("ok"):
        return _outcome(second)
    data = second["json"]
    data.setdefault("hints", {})
    data["hints"][STATUS_HINT] = "fallback"
    data["hints"][REASON_HINT] = reason
    return Outcome(True, second.get("status") or 200, data)


def _outcome(response: dict) -> Outcome:
    if response.get("ok"):
        return Outcome(True, response.get("status") or 200, response["json"])
    return Outcome(False, response.get("status") or 400, response.get("error"))
