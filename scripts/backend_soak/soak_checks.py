#!/usr/bin/env python3
"""Checks for the GraphHopper flood-road backend: the 48-hour soak (US-034) and the latency baselines (US-046).

Four subcommands.

    logs FILE...   Read `docker logs --timestamps` output and report requests by status, 5xx lines, and
                   error lines. Runs on any machine. Exit code 1 if it finds a 5xx or an error line, or
                   if a file has no timestamped line, because the read then failed.
    containers FILE
                   Read the `docker inspect` lines that run_soak.sh prints. Exit code 1 if a container
                   started after the soak start, was OOM killed, is not running, or could not be read.
    roads          Pick real edges from `edge_depth` whose depth lies between two vehicle limits,
                   call `POST /route` for each vehicle, and compare with the answer the limits give.
    latency        Time `POST /route` for a short, a medium, and a long trip.

`roads` and `latency` need `psycopg2` and the server's network, so run them inside the backend container:

    docker --context remote-server exec -i airflow_new-floodmap-backend-1 python - roads < soak_checks.py
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
_CANDIDATES = [Path("/app/scripts")]
if len(_HERE.parents) > 2:
    _CANDIDATES.append(_HERE.parents[2] / "floodmap/graphhopper-flood-road/scripts")
for _scripts in _CANDIDATES:
    if (_scripts / "flood_utils.py").exists():
        sys.path.insert(0, str(_scripts))
        break

from flood_utils import VEHICLE_PROFILES  # noqa: E402

VEHICLE_LIMIT_CM = {name: profile["threshold_cm"] for name, profile in VEHICLE_PROFILES.items()}

DOCKER_TS = re.compile(r"^(\d{4}-\d\d-\d\dT[\d:.]+Z) (.*)$")
ACCESS = re.compile(r'"(?:GET|POST|PUT|DELETE|HEAD|OPTIONS) \S+ HTTP/[\d.]+" (\d{3}) ')
GH_ERROR = re.compile(r"^(ERROR\b|java\.|javax\.|Caused by:|Exception in thread|\s+at )")


@dataclass
class LogReport:
    requests: int = 0
    by_status: dict[int, int] = field(default_factory=dict)
    server_errors: list[str] = field(default_factory=list)
    error_lines: list[str] = field(default_factory=list)
    bad_requests: int = 0
    first: str | None = None
    last: str | None = None


def scan_logs(lines) -> LogReport:
    report = LogReport()
    for raw in lines:
        line = raw.rstrip("\n")
        stamped = DOCKER_TS.match(line)
        body = stamped.group(2) if stamped else line
        if stamped:
            ts = stamped.group(1)
            report.first = ts if report.first is None else min(report.first, ts)
            report.last = ts if report.last is None else max(report.last, ts)
        access = ACCESS.search(body)
        if access:
            status = int(access.group(1))
            report.requests += 1
            report.by_status[status] = report.by_status.get(status, 0) + 1
            if status >= 500:
                report.server_errors.append(line)
        elif GH_ERROR.match(body):
            report.error_lines.append(line)
        elif "bad request:" in body:
            report.bad_requests += 1
    return report


CONTAINER_LINE = re.compile(
    r"^/?(?P<name>\S+) started=(?P<started>\S+) restarts=(?P<restarts>\d+) oomkilled=(?P<oom>true|false) status=(?P<status>\S+)$"
)


def _instant(value: str) -> datetime:
    trimmed = re.sub(r"(\.\d{6})\d+", r"\1", value.replace("Z", "+00:00"))
    moment = datetime.fromisoformat(trimmed)
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def judge_containers(lines, since: str) -> list[str]:
    """Problems that end the soak, one string each. An empty list means every container held the whole window."""
    start = _instant(since)
    problems = []
    seen = 0
    for line in (l.strip() for l in lines if l.strip()):
        match = CONTAINER_LINE.match(line)
        if not match:
            problems.append(f"could not read: {line[:200]}")
            continue
        seen += 1
        name = match["name"]
        if _instant(match["started"]) > start:
            problems.append(f"{name} started inside the window, at {match['started']}")
        if match["oom"] == "true":
            problems.append(f"{name} was OOM killed")
        if match["status"] != "running":
            problems.append(f"{name} has status {match['status']}")
    if not seen and not problems:
        problems.append("could not read any container line")
    return problems


def percentile(values, p: float):
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


def expected_outcome(depth_cm: float, vehicle: str) -> str:
    """What the depth bands of `flood_utils.DEPTH_BANDS` promise for one vehicle on one road piece.

    blocked: depth at or past the limit, band b4 (priority 0). No route may cross the piece.
    found:   from half the limit up to the limit, bands b2 and b3 (priority 0.2 and 0.05). The road is
             costly, not closed, so a route must exist but may detour.
    crosses: below half the limit, no penalty. A route between the neighbours must cross the piece.
    """
    limit = VEHICLE_LIMIT_CM[vehicle]
    if depth_cm >= limit:
        return "blocked"
    return "found" if depth_cm >= 0.5 * limit else "crosses"


def next_limit_cm(depth_cm: float):
    above = [limit for limit in VEHICLE_LIMIT_CM.values() if limit > depth_cm]
    return min(above) if above else None


def _project(lon: float, lat: float, lat0: float) -> tuple[float, float]:
    return lon * 111_320 * math.cos(math.radians(lat0)), lat * 110_540


def _distance_to_segment_m(point, a, b, lat0) -> float:
    px, py = _project(*point, lat0)
    ax, ay = _project(*a, lat0)
    bx, by = _project(*b, lat0)
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def route_passes_through(route, points, tol_m: float) -> bool:
    """True when every point lies within tol_m of the route's polyline."""
    if len(route) < 2:
        return False
    lat0 = route[0][1]
    return all(
        min(_distance_to_segment_m(point, a, b, lat0) for a, b in zip(route, route[1:])) <= tol_m
        for point in points
    )


def point_along(piece, fraction: float) -> tuple[float, float]:
    lat0 = piece[0][1]
    projected = [_project(lon, lat, lat0) for lon, lat in piece]
    lengths = [math.dist(a, b) for a, b in zip(projected, projected[1:])]
    target = fraction * sum(lengths)
    for (a, b), length in zip(zip(piece, piece[1:]), lengths):
        if target <= length or length == 0:
            t = 0.0 if length == 0 else target / length
            return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        target -= length
    return piece[-1]


def far_point(neighbour, piece, fraction: float = 0.9):
    """A point on the neighbour piece, most of the way from the shared end to its far end."""
    lat0 = piece[0][1]
    middle = point_along(piece, 0.5)
    near_first = math.dist(_project(*neighbour[0], lat0), _project(*middle, lat0)) <= math.dist(
        _project(*neighbour[-1], lat0), _project(*middle, lat0)
    )
    return point_along(list(neighbour) if near_first else list(neighbour)[::-1], fraction)


def judge_vehicle(outcome: str, directions, control) -> str:
    """Return "pass", "fail", or "skip".

    directions and control are lists of (route_found, route_crosses_piece), one per travel direction.
    The control is the same pair of points with no flood model. A pair is only a test when the control
    shows the promise can be seen: a dry route that crosses the piece, or at least exists.
    """
    flood_found = any(found for found, _ in directions)
    flood_crosses = any(found and crosses for found, crosses in directions)
    dry_found = any(found for found, _ in control)
    dry_crosses = any(found and crosses for found, crosses in control)
    if outcome == "found":
        return "skip" if not dry_found else ("pass" if flood_found else "fail")
    if not dry_crosses:
        return "skip"
    if outcome == "blocked":
        return "fail" if flood_crosses else "pass"
    return "pass" if flood_crosses else "fail"


# Real-world trips inside the model border (.claude/CLAUDE.md). Longitude first, as in an API body.
TRIPS = {
    "short": ([105.7550, 21.0250], [105.7620, 21.0255]),
    "medium": ([105.7712, 20.9902], [105.7952, 20.9815]),
    "long": ([105.7100, 20.9800], [105.7900, 21.0250]),
}

# (label, lower bound cm, upper bound cm), kept 0.3 cm clear of each limit so a rounding difference
# cannot move a road across it.
BUCKETS = [
    ("below every limit", 5.0, 19.7),
    ("motorbike blocked only", 20.3, 29.7),
    ("motorbike and car blocked", 30.3, 34.7),
    ("all but foot blocked", 35.3, 39.7),
    ("every vehicle blocked", 40.3, 10_000.0),
]

# edge_key is <osm_way_id>:<position along the way> (US-117), so the neighbours of an edge are the same way at
# position - 1 and + 1. An edge with no row is dry and is not a candidate, nor a neighbour, as before.
CURRENT_RUN_SQL = """
CREATE TEMP TABLE cur AS
SELECT e.edge_key AS segment_id, split_part(e.edge_key, ':', 1) AS way,
       split_part(e.edge_key, ':', 2)::int AS idx, d.depth_cm AS cm, e.geom AS g
FROM edge_depth d
JOIN graph_edge e USING (edge_key)
WHERE d.run_ts = %(run)s AND d.valid_time_utc = %(vt)s
"""

# run_ts and the body's run are the DAG's run name. valid_time_utc is naive UTC, and the route body's valid_time is
# local (+07:00) like the one the backend is called with.
LOCAL_OFFSET = timedelta(hours=7)

PICK_SQL = """
WITH cand AS (
    SELECT c.segment_id, c.cm, c.g, p.segment_id AS p_id, p.g AS p_g, x.segment_id AS x_id, x.g AS x_g
    FROM cur c
    JOIN cur p ON p.way = c.way AND p.idx = c.idx - 1
    JOIN cur x ON x.way = c.way AND x.idx = c.idx + 1
    WHERE c.cm >= %(lo)s AND c.cm <= %(hi)s
      AND p.cm < %(neighbour_floor)s AND x.cm < %(neighbour_floor)s
      AND ST_Length(p.g::geography) <= 120 AND ST_Length(x.g::geography) <= 120
      AND ST_GeometryType(c.g) = 'ST_LineString'
      AND ST_GeometryType(p.g) = 'ST_LineString' AND ST_GeometryType(x.g) = 'ST_LineString'
      AND ST_X(ST_StartPoint(c.g)) BETWEEN 105.7015 AND 105.7971
      AND ST_Y(ST_StartPoint(c.g)) BETWEEN 20.9754 AND 21.0269
    ORDER BY md5(c.segment_id)
    LIMIT %(sample)s
)
SELECT c.segment_id, c.cm, ST_AsGeoJSON(c.g), ST_AsGeoJSON(c.p_g), ST_AsGeoJSON(c.x_g)
FROM cand c
WHERE NOT EXISTS (
    SELECT 1 FROM cur n
    WHERE n.segment_id NOT IN (c.segment_id, c.p_id, c.x_id)
      AND n.cm >= %(neighbour_floor)s AND ST_DWithin(n.g, c.g, 0.0016))
ORDER BY md5(c.segment_id)
LIMIT %(n)s
"""


def post_json(url: str, body: dict, timeout: float = 120.0):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload, status = json.load(response), response.status
    except urllib.error.HTTPError as error:
        payload, status = json.loads(error.read() or b"{}"), error.code
    return status, payload, (time.perf_counter() - started) * 1000


def route_coordinates(payload: dict) -> list:
    try:
        return [tuple(c[:2]) for c in payload["paths"][0]["points"]["coordinates"]]
    except (KeyError, IndexError, TypeError):
        return []


def resolve_run(cur, run_arg, valid_time_arg):
    """The run name and the naive UTC forecast time to check. Default: the newest registered run and its first step.
    `run_arg` is a run name or a local timestamp such as '2026-10-02 02:15:00'. `valid_time_arg` is ISO, local when
    it has no offset."""
    if run_arg is None:
        cur.execute("SELECT max(run_ts) FROM edge_depth_run")
        run = cur.fetchone()[0]
        if run is None:
            raise SystemExit("edge_depth_run has no run")
    else:
        run = datetime.fromisoformat(run_arg).strftime("%Y%m%dT%H%M%S") if "-" in run_arg else run_arg
    if valid_time_arg is None:
        cur.execute("SELECT valid_times[1] FROM edge_depth_run WHERE run_ts = %s", (run,))
        row = cur.fetchone()
        if row is None or row[0] is None:
            raise SystemExit(f"edge_depth_run has no run {run}")
        return run, row[0]
    parsed = datetime.fromisoformat(valid_time_arg)
    if parsed.tzinfo is None:
        return run, parsed - LOCAL_OFFSET
    return run, parsed.astimezone(timezone.utc).replace(tzinfo=None)


def engine_cell(hints, valid_times):
    """The (run, naive UTC forecast time) the time-aware engine judged, or None when the hints carry no `td.run`.
    The engine departs at `td.departure` (epoch seconds) and floors it to a step, so the cell is the latest of the
    run's `valid_times` at or before the departure, or the first one when the departure is earlier."""
    run = (hints or {}).get("td.run")
    if not run or not valid_times:
        return None
    departure = datetime.fromtimestamp(float(hints["td.departure"]), timezone.utc).replace(tzinfo=None)
    steps = sorted(valid_times)
    return run, max((t for t in steps if t <= departure), default=steps[0])


def probe_engine_cell(cur, backend):
    start, end = TRIPS["short"]
    _, payload, _ = post_json(f"{backend}/route", {"points": [start, end], "profile": "motorbike",
                                                   "points_encoded": False, "instructions": False})
    hints = payload.get("hints") if isinstance(payload, dict) else None
    run = (hints or {}).get("td.run")
    if not run:
        return None
    cur.execute("SELECT valid_times FROM edge_depth_run WHERE run_ts = %s", (run,))
    row = cur.fetchone()
    return engine_cell(hints, row[0] if row else None)


def pick_roads(cur, run, vt, per_bucket):
    """Up to `per_bucket` isolated edges per depth bucket of one run and forecast time, as (bucket label, edge_key,
    depth in cm, edge GeoJSON, previous edge GeoJSON, next edge GeoJSON)."""
    cur.execute(CURRENT_RUN_SQL, {"run": run, "vt": vt})
    cur.execute("CREATE INDEX ON cur USING gist (g)")
    cur.execute("ANALYZE cur")
    picks = []
    for label, lo, hi in BUCKETS:
        floor = next_limit_cm(lo) if next_limit_cm(lo) is not None else 10_000.0
        cur.execute(PICK_SQL, {"lo": lo, "hi": hi, "neighbour_floor": floor, "n": per_bucket,
                               "sample": 200 * per_bucket})
        picks += [(label, *row) for row in cur.fetchall()]
    return picks


def run_roads(args) -> int:
    import os

    import psycopg2

    db_config = {"host": os.environ["POSTGRES_HOST"], "port": int(os.environ["POSTGRES_PORT"]),
                 "database": os.environ["POSTGRES_DB"], "user": os.environ["POSTGRES_USER"],
                 "password": os.environ["POSTGRES_PASSWORD"]}
    with psycopg2.connect(**db_config) as conn, conn.cursor() as cur:
        cell = probe_engine_cell(cur, args.backend) if args.run is None and args.valid_time is None else None
        run, vt = cell or resolve_run(cur, args.run, args.valid_time)
        picks = pick_roads(cur, run, vt, args.per_bucket)

    body_times = {"valid_time": (vt + LOCAL_OFFSET).strftime("%Y-%m-%dT%H:%M:%S+07:00"), "run": run}
    server_errors = 0
    rows = []
    for label, segment_id, cm, piece_json, before_json, after_json in picks:
        piece = [tuple(c) for c in json.loads(piece_json)["coordinates"]]
        start = far_point([tuple(c) for c in json.loads(before_json)["coordinates"]], piece)
        end = far_point([tuple(c) for c in json.loads(after_json)["coordinates"]], piece)
        waypoints = [point_along(piece, 0.2), point_along(piece, 0.8)]
        for vehicle in VEHICLE_LIMIT_CM:
            outcome = expected_outcome(cm, vehicle)
            directions, control = [], []
            for a, b in ((start, end), (end, start)):
                for extra, sink in ((body_times, directions), ({}, control)):
                    status, payload, _ = post_json(
                        f"{args.backend}/route",
                        {"points": [list(a), list(b)], "profile": vehicle, "points_encoded": False,
                         "instructions": False, **extra},
                    )
                    if status >= 500:
                        server_errors += 1
                    coords = route_coordinates(payload)
                    sink.append((status == 200 and bool(coords), route_passes_through(coords, waypoints, args.tol_m)))
            verdict = judge_vehicle(outcome, directions, control)
            rows.append({"bucket": label, "edge_key": segment_id, "depth_cm": cm,
                         "vehicle": vehicle, "expected": outcome, "flood": directions, "control": control,
                         "verdict": verdict})
    failures = sum(row["verdict"] == "fail" for row in rows)
    summary = {}
    for row in rows:
        key = f'{row["expected"]}:{row["verdict"]}'
        summary[key] = summary.get(key, 0) + 1
    print(json.dumps({"run": run, "valid_time_utc": vt.isoformat(), "roads": len(picks), "checks": len(rows),
                      "summary": summary, "failures": failures, "server_errors": server_errors,
                      "failed_rows": [row for row in rows if row["verdict"] == "fail"],
                      **({"rows": rows} if args.verbose else {})}, indent=1))
    return 1 if failures or server_errors else 0


def flood_custom_model(features: list) -> dict:
    """The same priority chain as `flood_areas.build_custom_model`: deepest band first, else_if after the first."""
    priority = [{("if" if i == 0 else "else_if"): f"in_{f['id']}", "multiply_by": str(f["properties"]["multiply_by"])}
                for i, f in enumerate(features)]
    return {"priority": priority, "areas": {"type": "FeatureCollection", "features": features}}


def run_latency(args) -> int:
    import os
    import urllib.parse

    flood_fields = {"valid_time": args.valid_time, "run": args.run}
    models = {}
    for vehicle in ("motorbike", "car"):
        query = urllib.parse.urlencode({**flood_fields, "vehicle_type": vehicle})
        with urllib.request.urlopen(f"{args.backend}/flood/areas?{query}", timeout=120) as response:
            collection = json.load(response)
        models[vehicle] = flood_custom_model(collection["features"])

    def body(vehicle, a, b, **extra):
        return {"points": [a, b], "profile": vehicle, "points_encoded": False, "instructions": False, **extra}

    targets = [
        ("A graphhopper, no flood model", args.graphhopper,
         lambda v, a, b, i: body(v, a, b, **{"ch.disable": True})),
        ("B graphhopper, flood model of the run", args.graphhopper,
         lambda v, a, b, i: body(v, a, b, **{"ch.disable": True, "custom_model": models[v]})),
        ("C floodmap-backend, areas cached", args.backend,
         lambda v, a, b, i: body(v, a, b, **flood_fields)),
        ("D floodmap-backend, areas not cached", args.backend,
         lambda v, a, b, i: body(v, a, b, buffer=22.0 + (i + 1) * 1e-6, **flood_fields)),
    ]
    results = {}
    load_before = Path("/proc/loadavg").read_text().split()[:3]
    for label, base, make in targets:
        for trip, (a, b) in TRIPS.items():
            for vehicle in ("motorbike", "car"):
                for i in range(args.warmup):
                    post_json(f"{base}/route", make(vehicle, a, b, -1 - i))
                timings, statuses, distance = [], {}, None
                for i in range(args.requests):
                    status, payload, ms = post_json(f"{base}/route", make(vehicle, a, b, i))
                    timings.append(ms)
                    statuses[status] = statuses.get(status, 0) + 1
                    if status == 200:
                        distance = round(payload["paths"][0]["distance"])
                results[f"{label} | {trip} | {vehicle}"] = {
                    "p50_ms": round(percentile(timings, 50), 1), "p95_ms": round(percentile(timings, 95), 1),
                    "max_ms": round(max(timings), 1), "statuses": statuses, "road_distance_m": distance}
    load_after = Path("/proc/loadavg").read_text().split()[:3]
    print(json.dumps({"requests_per_cell": args.requests, "cpus": os.cpu_count(), "loadavg_before": load_before,
                      "loadavg_after": load_after, "trips": TRIPS, "results": results}, indent=1))
    return 0


def latency_table(data: dict) -> str:
    """One row per target and trip. A (!) marks a cell where some request did not return 200."""
    rows: dict[tuple[str, str], dict[str, dict]] = {}
    for key, cell in data["results"].items():
        target, trip, vehicle = [part.strip() for part in key.split("|")]
        rows.setdefault((target, trip), {})[vehicle] = cell

    def text(cell):
        if cell is None:
            return "-"
        flag = "" if set(cell["statuses"]) <= {"200"} else " (!)"
        return f"{cell['p50_ms']} / {cell['p95_ms']}{flag}"

    width = max([23] + [len(target) + 2 for target, _ in rows])
    lines = ["target".ljust(width) + "trip".ljust(9) + "motorbike p50/p95 ms".ljust(23) + "car p50/p95 ms".ljust(17) + "road m"]
    for (target, trip), cells in rows.items():
        distance = next((c["road_distance_m"] for c in (cells.get("motorbike"), cells.get("car")) if c), None)
        lines.append(target.ljust(width) + trip.ljust(9) + text(cells.get("motorbike")).ljust(23)
                     + text(cells.get("car")).ljust(17) + str(distance))
    return "\n".join(lines)


def run_latency_table(args) -> int:
    print(latency_table(json.loads(Path(args.file).read_text())))
    return 0


def run_logs(args) -> int:
    code = 0
    for path in args.files:
        lines = Path(path).read_text(errors="replace").splitlines()
        report = scan_logs(lines)
        if report.first is None:
            first = next((l for l in lines if l.strip()), "(the file is empty)")
            print(f"{path}: no timestamped lines. The read failed, or the container logged nothing since the soak start. First line: {first[:300]}")
            code = 1
            continue
        print(f"{path}: {report.first} to {report.last}, {report.requests} requests, "
              f"by status {dict(sorted(report.by_status.items()))}, {report.bad_requests} bad-request lines, "
              f"{len(report.server_errors)} 5xx, {len(report.error_lines)} error lines")
        for line in report.server_errors + report.error_lines:
            print("  " + line[:300])
        code = 1 if report.server_errors or report.error_lines else code
    return code


def run_containers(args) -> int:
    problems = judge_containers(Path(args.file).read_text(errors="replace").splitlines(), args.since)
    for problem in problems:
        print("  " + problem)
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    logs = sub.add_parser("logs")
    logs.add_argument("files", nargs="+")
    logs.set_defaults(func=run_logs)
    containers = sub.add_parser("containers")
    containers.add_argument("file")
    containers.add_argument("--since", required=True, help="the soak start, for example 2026-10-02T00:45:00+07:00")
    containers.set_defaults(func=run_containers)
    roads = sub.add_parser("roads")
    roads.add_argument("--backend", default="http://localhost:8010")
    roads.add_argument("--run", help="run name or local timestamp, for example 20261002T021500. Default: the cell the engine judges, else the newest run.")
    roads.add_argument("--valid-time", help="forecast time, for example 2026-10-02T02:15:00+07:00. Default: the cell the engine judges, else the run's first step.")
    roads.add_argument("--per-bucket", type=int, default=4)
    roads.add_argument("--tol-m", type=float, default=6.0)
    roads.add_argument("--verbose", action="store_true", help="print every check, not only the failed ones")
    roads.set_defaults(func=run_roads)
    latency = sub.add_parser("latency")
    latency.add_argument("--backend", default="http://localhost:8010")
    latency.add_argument("--graphhopper", default="http://graphhopper:8989")
    latency.add_argument("--valid-time", required=True, help="for example 2026-10-02T02:15:00+07:00")
    latency.add_argument("--run", required=True, help="for example 20261002T021500")
    latency.add_argument("--requests", type=int, default=30)
    latency.add_argument("--warmup", type=int, default=3)
    latency.set_defaults(func=run_latency)
    table = sub.add_parser("latency-table")
    table.add_argument("file")
    table.set_defaults(func=run_latency_table)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
