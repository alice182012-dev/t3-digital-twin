"""The reference Graph of the real road network, read from the export of java/time-aware-routing/ (format 2).

Each GraphHopper edge becomes an arc in both directions with the edge's id. The export holds no one-way flag
and no speed, so one-way roads are open both ways and the travel time of an edge is its length at one free-flow
speed. A result from this graph must say both. Pure but for the file reads.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_REFERENCE = str(HERE.parent / "routing_reference")
if _REFERENCE not in sys.path:
    sys.path.insert(0, _REFERENCE)

from sampling import distance_m  # noqa: E402
from sticky_reference import Edge, Graph  # noqa: E402

DEFAULT_SPEED_MPS = 30 / 3.6
_POINT = re.compile(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)")


def wkt_length_m(wkt: str) -> float:
    points = [(float(a), float(b)) for a, b in _POINT.findall(wkt)]
    return sum(distance_m(a, b) for a, b in zip(points, points[1:]))


def load_graph(export_dir, speed_mps: float = DEFAULT_SPEED_MPS) -> tuple[Graph, str]:
    """The graph and the graph hash of the export. Raises ValueError for a format-1 export, which has no nodes."""
    export_dir = Path(export_dir)
    meta = json.loads((export_dir / "graph.json").read_text(encoding="utf-8"))
    if meta["format_version"] < 2:
        raise ValueError("a format-1 export has no base_node and adj_node")
    edges = []
    with open(export_dir / "edges.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            edges.append(Edge(int(row["edge_id"]), int(row["base_node"]), int(row["adj_node"]),
                              wkt_length_m(row["wkt"]) / speed_mps))
    if len(edges) != meta["edge_count"]:
        raise ValueError(f"{len(edges)} rows in edges.csv, edge_count {meta['edge_count']}")
    return Graph(edges, both_directions=True), meta["graph_hash"]
