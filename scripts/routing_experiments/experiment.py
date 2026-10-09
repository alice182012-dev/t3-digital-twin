#!/usr/bin/env python3
"""The harness of the routing paper experiments: how often a planned route meets a closed road on arrival (US-091).

For every pair, vehicle, table, and departure step, the planner plans a route on that step, and the re-walk
enters each edge at its free-flow arrival time and reads the depth there under three step rules. The result file
holds every route and a summary by storm, stage, vehicle, length class, departure step, and rule. The storm and the
stage are labels the caller gives. The harness does not compute them from the tables.

    python experiment.py sample --per-class 30 --seed 1 --out pairs.json
    python experiment.py run --model single_timestep --storm "..." --table-set "STAGE=/path/a.bin,/path/b.bin" \\
        --pairs pairs.json --out result.json [--backend URL] [--departure-steps 0,1,2] [--slow-min-depth-cm N --slow-factor F]

`run` calls POST /route on the backend, so it runs where the backend is reachable (the Airflow worker). The model
is set on the backend by TIME_AWARE_ROUTING; --model only labels the run, and model_check counts routes that
disagree with the label.
"""

from __future__ import annotations

import argparse
import json
import time
import statistics
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

HERE = Path(__file__).resolve().parent
for folder in (HERE.parent / "edge_depth", HERE.parent / "routing_reference", HERE.parent / "backend_soak"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import edge_depth_table  # noqa: E402
import sticky_reference as ref  # noqa: E402
from planner import PlanFailure, Planner, PlanRequest, http_planner  # noqa: E402
from rewalk import SlowDown, StepRule, rewalk  # noqa: E402
from sampling import LENGTH_CLASSES, Pair, sample_pairs  # noqa: E402

VEHICLES = ("motorbike", "car", "truck", "foot")
MODELS = ("single_timestep", "sticky")
MARGIN_S = ref.DEFAULT_MARGIN_S
ENGINE_RAN = ("applied", "unknown")


def vehicle_limits() -> dict[str, int]:
    """The deployed limits, read from VEHICLE_PROFILES (US-074 owns them)."""
    from soak_checks import VEHICLE_LIMIT_CM

    return {v: VEHICLE_LIMIT_CM[v] for v in VEHICLES}


@dataclass(frozen=True)
class TableSet:
    stage: str
    tables: tuple[edge_depth_table.EdgeDepthTable, ...]

    @classmethod
    def load(cls, stage: str, paths: Sequence[Path]) -> TableSet:
        return cls(stage, tuple(edge_depth_table.read_table(Path(p)) for p in paths))

    def describe(self) -> dict:
        return {"stage": self.stage, "runs": [t.header.run_name for t in self.tables],
                "graph_hashes": sorted({t.header.graph_hash for t in self.tables})}


def default_departure_steps(table_sets: Sequence[TableSet]) -> tuple[int, ...]:
    """Every step but the last: a route that leaves on the last step can only read the last step."""
    fewest = min(t.header.step_count for s in table_sets for t in s.tables)
    return tuple(range(fewest - 1))


def _walk_json(walk) -> dict:
    return {"violating_edges": walk.violating_edges, "worst_over_limit_cm": walk.worst_over_limit_cm,
            "worst_edge_id": walk.worst_edge_id, "first_violation_s": walk.first_violation_s,
            "beyond_horizon": walk.beyond_horizon, "edges_outside_table": walk.edges_outside_table,
            "violations": [{"position": v.position, "edge_id": v.edge_id, "arrival_s": v.arrival_s, "step": v.step,
                            "depth_cm": v.depth_cm} for v in walk.violations]}


def _plan_and_walk(planner, request, table, step, limit, slowdown, margin_s, now) -> dict:
    step_seconds = tuple(t.timestamp() for t in table.header.step_times)
    record = {"pair": request.pair.name, "length_class": request.pair.length_class, "vehicle": request.vehicle,
              "run": table.header.run_name, "departure_step": step, "valid_time": request.valid_time}
    sent_at = now()
    outcome = planner(request)
    if isinstance(outcome, PlanFailure):
        record.update(status=outcome.status, message=outcome.message, cannot_find_point=outcome.cannot_find_point)
        return record
    # The engine reports the step that holds the departure as td.departure, and travels from the time of the request
    # (US-096). The window of steps starts at the first, the clock at the second.
    window_start = float(outcome.engine.get("departure", step_seconds[step]))
    departure = max(sent_at, window_start) if "departure" in outcome.engine else window_start
    sticky = ref.StickyClosure(step_seconds, lambda e, s: _depth_or_dry(table, e, s), limit, departure_s=departure,
                               margin_s=margin_s, window_start_s=window_start)
    record.update(
        status=200, distance_m=outcome.distance_m, engine=outcome.engine, departure_s=departure,
        edge_ids=list(outcome.route.edge_ids), edge_seconds=list(outcome.route.edge_seconds),
        walks={rule.value: _walk_json(rewalk(outcome.route, departure, step_seconds, table.depth_cm, limit, rule, slowdown))
               for rule in StepRule},
        sticky_crossings=len(ref.find_crossings(outcome.route.edge_ids, outcome.route.edge_seconds, sticky)),
    )
    return record


def _depth_or_dry(table, edge_id: int, step: int) -> int:
    return table.depth_cm(edge_id, step) if 0 <= edge_id < table.header.edge_count else 0


def _summary(records: list[dict], storm: str) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        groups.setdefault((r["stage"], r["vehicle"], r["length_class"], r["departure_step"]), []).append(r)
    rows = []
    order = lambda key: (key[0], VEHICLES.index(key[1]), LENGTH_CLASSES.index(key[2]), key[3])  # noqa: E731
    for (stage, vehicle, cls, step), group in sorted(groups.items(), key=lambda kv: order(kv[0])):
        routed = [r for r in group if r["status"] == 200]
        dropped = sum(bool(r.get("cannot_find_point")) for r in group)
        for rule in StepRule:
            walks = [r["walks"][rule.value] for r in routed]
            bad = [w for w in walks if w["violating_edges"]]
            rows.append({
                "storm": storm, "stage": stage, "vehicle": vehicle, "length_class": cls, "departure_step": step,
                "rule": rule.value, "routes": len(walks), "violating_routes": len(bad),
                "violation_rate": round(len(bad) / len(walks), 4) if walks else None,
                "worst_over_limit_cm_max": max((w["worst_over_limit_cm"] for w in bad), default=None),
                "violating_edges_mean": round(float(statistics.mean(w["violating_edges"] for w in bad)), 3) if bad else None,
                "first_violation_s_median": float(statistics.median(w["first_violation_s"] for w in bad)) if bad else None,
                "dropped_cannot_find_point": dropped, "no_route": len(group) - len(routed) - dropped,
            })
    return rows


def _sticky_check(records: list[dict], table_sets: Sequence[TableSet], margin_s: float) -> dict:
    """The engine passes when no route enters a road the sticky rule closes, and no route violates under a step
    rule whose step always falls inside the sticky window [departure, arrival + margin]."""
    gaps = [b.timestamp() - a.timestamp() for s in table_sets for t in s.tables
            for a, b in zip(t.header.step_times, t.header.step_times[1:])]
    widest = max(gaps, default=0.0)
    lookahead = {StepRule.AT_OR_BEFORE: 0.0, StepRule.NEAREST: widest / 2, StepRule.WORSE_OF_TWO: widest}
    covered = [rule.value for rule in StepRule if lookahead[rule] <= margin_s]
    routed = [r for r in records if r["status"] == 200]
    by_rule = {rule.value: sum(r["walks"][rule.value]["violating_edges"] > 0 for r in routed) for rule in StepRule}
    crossings = sum(r["sticky_crossings"] > 0 for r in routed)
    return {"routes": len(routed), "sticky_crossings": crossings, "violations_by_rule": by_rule,
            "rules_the_margin_covers": covered,
            "passed": bool(routed) and crossings == 0 and all(by_rule[rule] == 0 for rule in covered)}


def _model_check(records: list[dict], model: str) -> dict:
    routed = [r for r in records if r["status"] == 200]
    ran = [r.get("engine", {}).get("status") in ENGINE_RAN for r in routed]
    return {"routes": len(routed), "not_this_model": sum(ran) if model == "single_timestep" else ran.count(False)}


def _iso(t: datetime) -> str:
    return t.isoformat()


def run_experiment(
    *,
    model: str,
    storm: str,
    pairs: Sequence[Pair],
    table_sets: Sequence[TableSet],
    limits: dict[str, int],
    planner: Planner,
    departure_steps: Sequence[int],
    slowdown: SlowDown | None = None,
    margin_s: float = MARGIN_S,
    valid_time: Callable[[str, datetime], str] = lambda run, t: _iso(t),
    now: Callable[[], float] = time.time,
) -> dict:
    """valid_time(run, step time) gives the string the backend expects for a step, so the server run can use the
    exact strings /flood/timesteps lists."""
    if model not in MODELS:
        raise ValueError(f"model {model!r} is not one of {MODELS}")
    records = []
    for table_set in table_sets:
        for table in table_set.tables:
            for vehicle, limit in limits.items():
                for pair in pairs:
                    for step in departure_steps:
                        request = PlanRequest(pair, vehicle, valid_time(table.header.run_name, table.header.step_times[step]),
                                              table.header.run_name)
                        record = _plan_and_walk(planner, request, table, step, limit, slowdown, margin_s, now)
                        records.append({"stage": table_set.stage, **record})
    return {
        "story": "US-091", "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model, "storm": storm, "case": slowdown.label if slowdown else "free flow",
        "depth_source": "edge depth table (3Di model output), one file per run",
        "margin_s": margin_s, "rules": [r.value for r in StepRule], "vehicles": dict(limits),
        "table_sets": [s.describe() for s in table_sets], "departure_steps": list(departure_steps),
        "pairs": [p.to_json() for p in pairs],
        "summary": _summary(records, storm),
        "sticky_check": _sticky_check(records, table_sets, margin_s),
        "model_check": _model_check(records, model),
        "routes": records,
    }


def write_result(path: Path, result: dict) -> None:
    Path(path).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")


def backend_valid_times(backend: str, runs: Sequence[str]) -> dict[tuple[str, int], str]:
    """{(run, epoch seconds): valid_time} as /flood/timesteps lists them."""
    out = {}
    for run in runs:
        with urllib.request.urlopen(f"{backend}/flood/timesteps?run={run}", timeout=60) as response:
            for step in json.load(response)["timesteps"]:
                moment = datetime.fromisoformat(step["valid_time"].replace("Z", "+00:00"))
                out[(run, int(moment.timestamp()))] = step["valid_time"]
    return out


def _parse_table_set(text: str) -> TableSet:
    stage, _, paths = text.partition("=")
    if not stage or not paths:
        raise argparse.ArgumentTypeError(f"{text!r} is not STAGE=path[,path...]")
    return TableSet.load(stage, [Path(p) for p in paths.split(",")])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sample")
    p.add_argument("--per-class", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("run")
    p.add_argument("--model", choices=MODELS, required=True)
    p.add_argument("--storm", required=True, help="the storm behind the tables, for example the 2026-09-16 IMERG replay")
    p.add_argument("--table-set", type=_parse_table_set, action="append", required=True, help="STAGE=path[,path...]")
    p.add_argument("--pairs", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--backend", default="http://floodmap-backend:8010")
    p.add_argument("--departure-steps", help="comma-separated step indexes; every step but the last when left out")
    p.add_argument("--slow-min-depth-cm", type=int)
    p.add_argument("--slow-factor", type=float)
    args = parser.parse_args(argv)

    if args.command == "sample":
        pairs = sample_pairs(args.per_class, args.seed)
        Path(args.out).write_text(json.dumps([p.to_json() for p in pairs], indent=1) + "\n", encoding="utf-8")
        print(f"{len(pairs)} pairs, {args.per_class} per class, seed {args.seed}, written to {args.out}")
        return 0

    if (args.slow_min_depth_cm is None) != (args.slow_factor is None):
        parser.error("--slow-min-depth-cm and --slow-factor go together")
    slowdown = SlowDown(args.slow_min_depth_cm, args.slow_factor) if args.slow_factor is not None else None
    steps = (tuple(int(s) for s in args.departure_steps.split(",")) if args.departure_steps
             else default_departure_steps(args.table_set))
    runs = [t.header.run_name for s in args.table_set for t in s.tables]
    listed = backend_valid_times(args.backend, runs)
    missing = [(t.header.run_name, t.header.step_times[i].isoformat()) for s in args.table_set for t in s.tables
               for i in steps if (t.header.run_name, int(t.header.step_times[i].timestamp())) not in listed]
    if missing:
        print(f"FAIL: the backend lists no step for {len(missing)} (run, step) pairs, first {missing[:3]}")
        return 1
    result = run_experiment(
        model=args.model, storm=args.storm, pairs=[Pair.from_json(d) for d in json.loads(Path(args.pairs).read_text())],
        table_sets=args.table_set, limits=vehicle_limits(), planner=http_planner(args.backend), departure_steps=steps,
        slowdown=slowdown, valid_time=lambda run, t: listed[(run, int(t.timestamp()))],
    )
    write_result(Path(args.out), result)
    check, model_check = result["sticky_check"], result["model_check"]
    print(f"{model_check['routes']} routes, case {result['case']}, written to {args.out}")
    print(f"violating routes by rule: {check['violations_by_rule']}; sticky crossings: {check['sticky_crossings']}")
    if model_check["not_this_model"]:
        print(f"FAIL: {model_check['not_this_model']} routes were not planned by the {args.model} model; check TIME_AWARE_ROUTING")
        return 1
    if args.model == "sticky":
        print("PASS: no sticky route meets a closed road" if check["passed"] else "FAIL: a sticky route meets a closed road")
        return 0 if check["passed"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
