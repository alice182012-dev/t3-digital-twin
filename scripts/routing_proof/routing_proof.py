#!/usr/bin/env python3
"""The proof tooling for the time-aware engine on the server (US-055). Pure parts are tested in test_routing_proof.py.

Run it in the Airflow worker, which has the repo's scripts and the table volume and is on the compose network:

    docker exec airflow_new-airflow-worker-1 python /opt/airflow/scripts/routing_proof/routing_proof.py <command> ...

Commands:
  latency     p50 and p95 of POST /route through floodmap-backend (flag on) against the baseline of US-046, factor 2.
  pairs       Route a fixed set of pairs through the backend and write the routes, with their edge ids and times.
  compare     The share of routes that change between a run with the flag off and one with it on, and the median detour ratio.
  crossings   Walk every route over the depth table and list each road entered while closed (the checker of US-047).
  departures  Ask POST /route/departures for each trip and print the answer.

The baseline is target C of "Latency of POST /route, 2026-10-02" in artifacts/docs/blockers/routing-not-time-aware.md, the
path the app takes (`POST /route` through floodmap-backend with the areas cached), and target B is kept for comparison. The
user set the factor of 2 on 2026-10-02.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
for folder in (HERE.parent / "backend_soak", HERE.parent / "edge_depth", HERE.parent / "routing_reference"):
    sys.path.insert(0, str(folder))

import edge_depth_table  # noqa: E402
import sticky_reference as ref  # noqa: E402
from soak_checks import TRIPS, VEHICLE_LIMIT_CM, percentile, post_json  # noqa: E402

FACTOR = 2.0
MARGIN_S = 600
VEHICLES = ("motorbike", "car", "truck", "foot")
ENGINE_KNOWN = ("applied", "unknown")

BASELINE_B = {
    ('short', 'motorbike'): (189.1, 287.5),
    ('short', 'car'): (153.1, 219.4),
    ('medium', 'motorbike'): (381.5, 491.5),
    ('medium', 'car'): (276.9, 336.1),
    ('long', 'motorbike'): (1683.8, 1926.4),
    ('long', 'car'): (1856.7, 2279.4),
}

BASELINE_C = {
    ('short', 'motorbike'): (136.5, 157.6),
    ('short', 'car'): (125.7, 161.9),
    ('medium', 'motorbike'): (222.4, 241.7),
    ('medium', 'car'): (158.6, 185.6),
    ('long', 'motorbike'): (1892.5, 2407.7),
    ('long', 'car'): (2759.2, 3720.8),
}


def parse_baseline(text: str, target: str) -> dict:
    """The p50 and p95 cells of a target's rows in the latency table of the vault: {(trip, vehicle): (p50, p95)}."""
    out = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].startswith(target):
            for vehicle, cell in zip(("motorbike", "car"), cells[2:]):
                p50, p95 = (float(x.replace(",", "")) for x in cell.split("/"))
                out[(cells[1], vehicle)] = (p50, p95)
    return out


# ---------------------------------------------------------------------------------------------------- latency


@dataclass
class Cell:
    trip: str
    vehicle: str
    p50: float
    p95: float
    base_p50: float | None
    base_p95: float | None
    ok: bool
    note: str


@dataclass
class LatencyVerdict:
    cells: list[Cell]
    factor: float

    @property
    def passed(self) -> bool:
        return bool(self.cells) and all(c.ok for c in self.cells)


def judge_latency(measured: dict, baseline: dict, factor: float = FACTOR) -> LatencyVerdict:
    """measured: {(trip, vehicle): {p50_ms, p95_ms, statuses, td_statuses}}. A cell passes when both percentiles are within
    factor times the baseline, every request returned 200, and the engine ran (no fallback) on every request."""
    cells = []
    for (trip, vehicle), cell in measured.items():
        base = baseline.get((trip, vehicle))
        notes = []
        if base is None:
            notes.append("no baseline")
        if set(cell["statuses"]) - {"200"}:
            notes.append("not every request returned 200")
        if set(cell.get("td_statuses", {})) - set(ENGINE_KNOWN):
            notes.append("the engine did not run on every request")
        ok_latency = base is not None and cell["p50_ms"] <= factor * base[0] and cell["p95_ms"] <= factor * base[1]
        if base is not None and not ok_latency:
            notes.append("OVER the limit")
        cells.append(Cell(trip, vehicle, cell["p50_ms"], cell["p95_ms"], base[0] if base else None, base[1] if base else None,
                          ok_latency and not [n for n in notes if n != "OVER the limit"], ", ".join(notes)))
    return LatencyVerdict(cells, factor)


def render_latency(verdict: LatencyVerdict) -> str:
    lines = [f"{'trip':<8}{'vehicle':<11}{'p50 ms':>9}{'p95 ms':>9}{'base p50':>10}{'base p95':>10}{'limit p50':>11}{'limit p95':>11}  note"]
    for c in verdict.cells:
        limit50 = f"{verdict.factor * c.base_p50:.1f}" if c.base_p50 is not None else ""
        limit95 = f"{verdict.factor * c.base_p95:.1f}" if c.base_p95 is not None else ""
        lines.append(f"{c.trip:<8}{c.vehicle:<11}{c.p50:>9.1f}{c.p95:>9.1f}{c.base_p50 if c.base_p50 is not None else '':>10}"
                     f"{c.base_p95 if c.base_p95 is not None else '':>10}{limit50:>11}{limit95:>11}  {c.note}")
    bad = sum(not c.ok for c in verdict.cells)
    lines.append("")
    lines.append(f"PASS: all {len(verdict.cells)} cells within {verdict.factor:g} times the baseline" if verdict.passed
                 else (f"FAIL: {bad} of {len(verdict.cells)} cells failed" if verdict.cells else "FAIL: nothing was measured"))
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------- pairs


def current_step(steps: list[dict], now: datetime) -> dict:
    """The step the map shows: the latest valid_time at or before now, or the earliest when every step is ahead (the frontend's rule)."""
    if not steps:
        raise ValueError("the backend lists no forecast step")
    parsed = [(datetime.fromisoformat(s["valid_time"]), s) for s in steps]
    at_or_before = [p for p in parsed if p[0] <= now]
    return max(at_or_before, key=lambda p: p[0])[1] if at_or_before else min(parsed, key=lambda p: p[0])[1]


def route_body(pair: dict, step: dict) -> dict:
    return {"points": [pair["from"], pair["to"]], "profile": pair["vehicle"], "points_encoded": False, "instructions": False,
            "details": ["edge_id", "time"], "valid_time": step["valid_time"], "run": step["run"]}


def make_record(pair: dict, status: int, payload: dict, requested_at: datetime) -> dict:
    record = {"name": pair["name"], "vehicle": pair["vehicle"], "from": pair["from"], "to": pair["to"],
              "requested_at": requested_at.timestamp(), "status": status, "distance": None, "time_ms": None,
              "edge_ids": [], "edge_times_ms": [], "td": {}}
    if status != 200:
        record["message"] = payload.get("message") or payload.get("error") or ""
        return record
    path = payload["paths"][0]
    details = path.get("details") or {}
    hints = payload.get("hints") or {}
    record.update(distance=path.get("distance"), time_ms=path.get("time"),
                  edge_ids=[d[2] for d in details.get("edge_id", [])], edge_times_ms=[d[2] for d in details.get("time", [])])
    record["td"] = {k.split(".", 1)[1]: v for k, v in hints.items() if k in ("td.status", "td.run", "td.departure", "td.reason")}
    return record


def _key(record: dict) -> tuple[str, str]:
    return record["name"], record["vehicle"]


def compare_runs(a: list[dict], b: list[dict]) -> dict:
    """A is today's model (flag off) and B the engine (flag on). Routes are equal when their edge ids are."""
    a_by, b_by = {_key(r): r for r in a}, {_key(r): r for r in b}
    compared = changed = 0
    ratios, not_compared = [], []
    for key in sorted(set(a_by) | set(b_by)):
        ra, rb = a_by.get(key), b_by.get(key)
        if not (ra and rb and ra["status"] == 200 and rb["status"] == 200 and ra["edge_ids"] and rb["edge_ids"]):
            not_compared.append(f"{key[0]}")
            continue
        compared += 1
        if ra["edge_ids"] != rb["edge_ids"]:
            changed += 1
            if ra["distance"]:
                ratios.append(rb["distance"] / ra["distance"])
    statuses: dict[str, int] = {}
    for r in b:
        if r["status"] == 200:
            s = r["td"].get("status", "none")
            statuses[s] = statuses.get(s, 0) + 1
    return {
        "compared": compared, "changed": changed,
        "percent_changed": round(100.0 * changed / compared, 1) if compared else 0.0,
        "median_detour_ratio": round(statistics.median(ratios), 3) if ratios else None,
        "not_compared": not_compared, "engine_statuses": statuses,
        "engine_ok": bool(statuses) and set(statuses) <= set(ENGINE_KNOWN),
    }


# ---------------------------------------------------------------------------------------------------- crossings


def _table_for(directory: Path, run: str | None):
    if run and (directory / f"{run}.bin").exists():
        return edge_depth_table.read_table(directory / f"{run}.bin")
    return edge_depth_table.read_latest_table(directory)


def check_crossings(records: Iterable[dict], table_dir: Path, limits: dict, margin_s: float = MARGIN_S) -> dict:
    """For each route, the roads it entered while closed, by the rule of US-050 with the departure of the engine
    (`td.departure`) or, when there is none, the step that contains the time of the request. {"name|vehicle": [crossing, ...]}."""
    found: dict[str, list] = {}
    for record in records:
        if record["status"] != 200 or not record["edge_ids"]:
            continue
        table = _table_for(Path(table_dir), record["td"].get("run"))
        steps = tuple(t.timestamp() for t in table.header.step_times)
        departure = record["td"].get("departure")
        if departure is None:
            before = [s for s in steps if s <= record["requested_at"]]
            departure = max(before) if before else record["requested_at"]
        rule = ref.StickyClosure(steps, lambda e, s, t=table: t.depth_cm(e, s) if 0 <= e < t.header.edge_count else 0,
                                 limits[record["vehicle"]], departure_s=float(departure), margin_s=margin_s)
        crossings = ref.find_crossings(record["edge_ids"], [m / 1000.0 for m in record["edge_times_ms"]], rule)
        found[f"{record['name']}|{record['vehicle']}"] = [
            {"position": c.position, "edge_id": c.edge_id, "arrival_s": c.arrival_s, "closing_step": c.closing_step} for c in crossings]
    return found


# ---------------------------------------------------------------------------------------------------- commands


def _current_step_from_backend(backend: str) -> dict:
    with urllib.request.urlopen(f"{backend}/flood/timesteps", timeout=60) as response:
        steps = json.load(response)["timesteps"]
    return current_step(steps, datetime.now(timezone.utc))


def _pairs(path: str | None) -> list[dict]:
    return json.loads(Path(path or HERE / "pairs.json").read_text(encoding="utf-8"))


def run_latency(args) -> int:
    step = _current_step_from_backend(args.backend)
    measured = {}
    for trip, (a, b) in TRIPS.items():
        for vehicle in ("motorbike", "car"):
            body = route_body({"name": trip, "vehicle": vehicle, "from": a, "to": b}, step)
            for _ in range(args.warmup):
                post_json(f"{args.backend}/route", body)
            timings, statuses, td = [], {}, {}
            for _ in range(args.requests):
                status, payload, ms = post_json(f"{args.backend}/route", body)
                timings.append(ms)
                statuses[str(status)] = statuses.get(str(status), 0) + 1
                if status == 200:
                    s = (payload.get("hints") or {}).get("td.status", "none")
                    td[s] = td.get(s, 0) + 1
            measured[(trip, vehicle)] = {"p50_ms": round(percentile(timings, 50), 1), "p95_ms": round(percentile(timings, 95), 1),
                                         "statuses": statuses, "td_statuses": td}
    verdict = judge_latency(measured, BASELINE_C, args.factor)
    print(render_latency(verdict))
    if args.out:
        Path(args.out).write_text(json.dumps({f"{t}|{v}": c for (t, v), c in measured.items()}, indent=1))
    return 0 if verdict.passed else 1


def run_pairs(args) -> int:
    step = _current_step_from_backend(args.backend)
    records = []
    for pair in _pairs(args.pairs):
        requested_at = datetime.now(timezone.utc)
        status, payload, _ = post_json(f"{args.backend}/route", route_body(pair, step))
        records.append(make_record(pair, status, payload, requested_at))
    Path(args.out).write_text(json.dumps(records, indent=1))
    routed = sum(r["status"] == 200 for r in records)
    print(f"{len(records)} pairs, {routed} routed, step {step['valid_time']} run {step['run']}, written to {args.out}")
    for r in records:
        if r["status"] != 200:
            print(f"  no route: {r['name']} {r['vehicle']}: {r.get('message', '')[:80]}")
    return 0 if routed else 1


def run_compare(args) -> int:
    a, b = json.loads(Path(args.a).read_text()), json.loads(Path(args.b).read_text())
    out = compare_runs(a, b)
    print(json.dumps(out, indent=1))
    ok = out["compared"] > 0 and out["engine_ok"]
    print("PASS: routes compared and the engine ran on every one" if ok else "FAIL: nothing compared, or the engine did not run on every route")
    return 0 if ok else 1


def run_crossings(args) -> int:
    limits = {v: VEHICLE_LIMIT_CM[v] for v in VEHICLES}
    code = 0
    for label, path, must_be_clean in (("engine (flag on)", args.b, True), ("today's model (flag off)", args.a, False)):
        if not path:
            continue
        found = check_crossings(json.loads(Path(path).read_text()), Path(args.table_dir), limits)
        crossing = {k: v for k, v in found.items() if v}
        print(f"{label}: {len(found)} routes checked, {len(crossing)} cross a closed road")
        for key, items in crossing.items():
            print(f"  {key}: {[(c['edge_id'], round(c['arrival_s'])) for c in items]}")
        if must_be_clean and (crossing or not found):
            code = 1
    print("PASS: no engine route crosses a road that is closed on arrival" if code == 0 else "FAIL: an engine route crosses a closed road, or none was checked")
    return code


def run_departures(args) -> int:
    bad = 0
    for trip, (a, b) in TRIPS.items():
        status, payload, ms = post_json(f"{args.backend}/route/departures", {"points": [a, b], "profile": args.vehicle})
        state = payload.get("status") if status == 200 else f"HTTP {status}"
        earliest = (payload.get("earliest_clear") or {}).get("leave_at") if status == 200 else None
        print(f"{trip:<7} {state:<12} run {payload.get('run')} age {payload.get('run_age_s')} s, earliest clear {earliest}, "
              f"{[c['status'] for c in payload.get('candidates', [])]}, {ms:.0f} ms")
        bad += state != "ok"
    print("PASS: the endpoint answered for every trip" if not bad else f"FAIL: {bad} trips did not get an answer")
    return 1 if bad else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("latency", run_latency), ("pairs", run_pairs), ("departures", run_departures)):
        p = sub.add_parser(name)
        p.add_argument("--backend", default="http://floodmap-backend:8010")
        p.set_defaults(func=func)
        if name == "latency":
            p.add_argument("--requests", type=int, default=30)
            p.add_argument("--warmup", type=int, default=3)
            p.add_argument("--factor", type=float, default=FACTOR)
            p.add_argument("--out")
        if name == "pairs":
            p.add_argument("--pairs")
            p.add_argument("--out", required=True)
        if name == "departures":
            p.add_argument("--vehicle", default="car")
    p = sub.add_parser("compare")
    p.add_argument("a", help="routes with the flag off")
    p.add_argument("b", help="routes with the flag on")
    p.set_defaults(func=run_compare)
    p = sub.add_parser("crossings")
    p.add_argument("--a", help="routes with the flag off, reported for contrast")
    p.add_argument("--b", required=True, help="routes with the flag on, which must be clean")
    p.add_argument("--table-dir", default="/opt/airflow/edge_depth_tables")
    p.set_defaults(func=run_crossings)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
