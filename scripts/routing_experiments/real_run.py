#!/usr/bin/env python3
"""The real-graph run of US-092 and US-093 on edge depth tables, offline.

Loads the format-2 graph export, samples node pairs inside the model border, and for every table and departure
step runs the vehicle-limit sweep (limit_sweep.py), the precaution-fraction sweep (precaution.py), and the
sticky versus arrival-only comparison (sticky_cost.py). The result file holds the notes a reader needs: one-way
roads are open both ways, and the travel time of an edge is its length at 30 km/h.

    python real_run.py --export DIR --table-set "STAGE=a.bin,b.bin" --per-class 20 --seed 1 --out result.json
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Sequence

HERE = Path(__file__).resolve().parent
for folder in (HERE.parent / "edge_depth", HERE.parent / "routing_reference", HERE.parent / "backend_soak"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import edge_depth_table  # noqa: E402
import sticky_reference as ref  # noqa: E402
from limit_sweep import conclusion_changes, sweep  # noqa: E402
from precaution import sweep_fraction  # noqa: E402
from real_graph import _POINT, DEFAULT_SPEED_MPS, load_graph  # noqa: E402
from sampling import BORDER, LENGTH_CLASSES, distance_m, length_class  # noqa: E402
from sticky_cost import compare, summarize  # noqa: E402

FRACTIONS = (0.25, 0.5, 0.75)
NOTES = (
    "One-way roads are open both ways: the export holds no one-way flag.",
    "The travel time of an edge is its length at 30 km/h: the export holds no speed.",
    "Depth comes from the edge depth tables only.",
)


def node_points(export_dir) -> dict[int, tuple[float, float]]:
    """Node id to (lon, lat), from the first and last point of each edge geometry."""
    points = {}
    with open(Path(export_dir) / "edges.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            found = _POINT.findall(row["wkt"])
            points[int(row["base_node"])] = (float(found[0][0]), float(found[0][1]))
            points[int(row["adj_node"])] = (float(found[-1][0]), float(found[-1][1]))
    return points


def sample_node_pairs(points: dict[int, tuple[float, float]], per_class: int, seed: int,
                      max_draws: int = 1_000_000) -> list[tuple[int, int]]:
    """per_class node pairs of each length class, both nodes inside the model border. Seeded."""
    inside = sorted(n for n, (lon, lat) in points.items()
                    if BORDER.lon_min <= lon <= BORDER.lon_max and BORDER.lat_min <= lat <= BORDER.lat_max)
    rng = random.Random(seed)
    found: dict[str, list[tuple[int, int]]] = {c: [] for c in LENGTH_CLASSES}
    for _ in range(max_draws):
        if all(len(v) == per_class for v in found.values()):
            break
        a, b = rng.choice(inside), rng.choice(inside)
        cls = length_class(distance_m(points[a], points[b]))
        if a != b and len(found[cls]) < per_class:
            found[cls].append((a, b))
    else:
        raise RuntimeError(f"{max_draws} draws did not fill every class: {({c: len(v) for c, v in found.items()})}")
    return [p for c in LENGTH_CLASSES for p in found[c]]


def _jsonable(value):
    if dataclasses.is_dataclass(value):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {("|".join(map(str, k)) if isinstance(k, tuple) else str(k)): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


_WORKER: dict = {}


def _init_worker(export_dir) -> None:
    _WORKER["graph"], _WORKER["hash"] = load_graph(export_dir)
    _WORKER["tables"] = {}


def _dense_rows(path: str, graph_hash: str):
    if path not in _WORKER["tables"]:
        table = edge_depth_table.require_graph_hash(edge_depth_table.read_table(Path(path)), graph_hash)
        _WORKER["tables"] = {path: (table.header, [table.edge_depths_cm(e) for e in range(table.header.edge_count)])}
    return _WORKER["tables"][path]


def _run_setting(task):
    """One (stage, table, departure step): the three experiments, on the graph of this process."""
    stage, path, step, pairs, limits, margin_s, fractions = task
    graph = _WORKER["graph"]
    header, rows = _dense_rows(str(path), _WORKER["hash"])
    step_seconds = tuple(t.timestamp() for t in header.step_times)

    def depth(edge_id: int, step_index: int) -> int:
        return rows[edge_id][step_index]

    key = (stage, header.run_name, step)
    departure = step_seconds[step]
    plan_limits = sorted(set(limits.values()))
    limit_result = sweep(graph, pairs, departure, step, step_seconds, depth,
                         lambda e: graph.edge(e).seconds * DEFAULT_SPEED_MPS, plan_limits, plan_limits)
    fraction_rows = {(*key, vehicle, fraction): row for (vehicle, fraction), row in
                     sweep_fraction(graph, pairs, departure, departure, step_seconds, depth, margin_s, limits, fractions).items()}
    sticky = [((*key, vehicle), compare(graph, o, d, departure, departure, step_seconds, depth, limit, margin_s))
              for vehicle, limit in limits.items() for o, d in pairs]
    return key, limit_result, fraction_rows, sticky


def run_real(export_dir, table_sets: Sequence[tuple[str, Sequence[Path]]], limits: dict[str, int],
             per_class: int, seed: int, steps: Sequence[int] | None = None, margin_s: float = ref.DEFAULT_MARGIN_S,
             fractions: Sequence[float] = FRACTIONS, jobs: int = 1) -> dict:
    graph_hash = json.loads((Path(export_dir) / "graph.json").read_text(encoding="utf-8"))["graph_hash"]
    pairs = sample_node_pairs(node_points(export_dir), per_class, seed)
    tasks = []
    for stage, paths in table_sets:
        for path in paths:
            header = edge_depth_table.read_table(Path(path)).header
            for step in steps if steps is not None else range(header.step_count - 1):
                tasks.append((stage, str(path), step, pairs, limits, margin_s, fractions))
    if jobs == 1:
        _init_worker(export_dir)
        done = [_run_setting(t) for t in tasks]
    else:
        with ProcessPoolExecutor(jobs, initializer=_init_worker, initargs=(export_dir,)) as pool:
            done = list(pool.map(_run_setting, tasks))
    limit_results = {key: result for key, result, _, _ in done}
    fraction_rows = {k: v for _, _, rows, _ in done for k, v in rows.items()}
    sticky_records = [r for _, _, _, records in done for r in records]
    baseline = next(iter(limit_results))
    return {
        "notes": list(NOTES), "graph_hash": graph_hash, "seed": seed, "per_class": per_class, "n_pairs": len(pairs),
        "limits": limits, "margin_s": margin_s,
        "table_sets": [{"stage": s, "runs": [Path(p).stem for p in ps]} for s, ps in table_sets],
        "us092_limit_sweep": _jsonable(limit_results),
        "us092_conclusion_changes_against": "|".join(map(str, baseline)),
        "us092_conclusion_changes": _jsonable(conclusion_changes(limit_results, baseline)),
        "us092_fraction_sweep": _jsonable(fraction_rows),
        "us093_sticky_vs_arrival_only": _jsonable(summarize(sticky_records)),
    }


def _table_set(text: str) -> tuple[str, list[Path]]:
    stage, _, paths = text.partition("=")
    if not stage or not paths:
        raise argparse.ArgumentTypeError(f"{text!r} is not STAGE=path[,path...]")
    return stage, [Path(p) for p in paths.split(",")]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--export", required=True)
    parser.add_argument("--table-set", type=_table_set, action="append", required=True)
    parser.add_argument("--per-class", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--departure-steps", help="comma-separated step indexes; every step but the last when left out")
    parser.add_argument("--jobs", type=int, default=1, help="worker processes; each loads the graph once")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    from experiment import vehicle_limits

    steps = tuple(int(s) for s in args.departure_steps.split(",")) if args.departure_steps else None
    result = run_real(args.export, args.table_set, vehicle_limits(), args.per_class, args.seed, steps, jobs=args.jobs)
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"{result['n_pairs']} pairs, {len(result['us092_limit_sweep'])} (stage, run, step) settings, written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
