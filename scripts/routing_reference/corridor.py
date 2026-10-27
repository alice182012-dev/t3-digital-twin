"""A road network built from OpenStreetMap ways, for the offline routing reference.

Story R2 (US-047). The input is a GeoJSON file of way LineStrings, such as
marie-curie/raster-first/roads.geojson. A vertex shared by two ways, or the end of a way, is a node.
The road between two nodes is one edge, with one edge per direction: edge `2k` runs forward and
`2k + 1` is its reverse, so `edge_id ^ 1` is the opposite direction. Ids are dense from 0, like
GraphHopper's. One-way tags are ignored, so every road runs both ways.
"""

from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Iterable

from sticky_reference import Edge, Graph

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Way:
    osm_id: str
    coords: tuple[tuple[float, float], ...]  # (lon, lat)


@dataclass(frozen=True)
class RoadEdge:
    id: int
    tail: int
    head: int
    length_m: float
    way_id: str


def load_ways(path: Path) -> list[Way]:
    collection = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Way(f["properties"].get("@id", ""), tuple((x, y) for x, y in f["geometry"]["coordinates"]))
        for f in collection["features"]
        if f["geometry"]["type"] == "LineString"
    ]


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1, lon2, lat2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(h))


class RoadNetwork:
    def __init__(self, node_xy: dict[int, tuple[float, float]], edges: tuple[RoadEdge, ...]) -> None:
        self.node_xy = node_xy
        self.edges = edges
        self._out: dict[int, list[RoadEdge]] = {}
        for e in edges:
            self._out.setdefault(e.tail, []).append(e)

    @classmethod
    def from_ways(cls, ways: Iterable[Way]) -> RoadNetwork:
        ways = list(ways)
        uses: dict[tuple[float, float], int] = {}
        for way in ways:
            for xy in way.coords:
                uses[xy] = uses.get(xy, 0) + 1
        node_ids: dict[tuple[float, float], int] = {}
        edges: list[RoadEdge] = []

        def node(xy: tuple[float, float]) -> int:
            return node_ids.setdefault(xy, len(node_ids))

        for way in ways:
            cuts = [i for i, xy in enumerate(way.coords) if i in (0, len(way.coords) - 1) or uses[xy] >= 2]
            for a, b in zip(cuts, cuts[1:]):
                piece = way.coords[a : b + 1]
                length = sum(_distance_m(p, q) for p, q in zip(piece, piece[1:]))
                tail, head = node(way.coords[a]), node(way.coords[b])
                edges.append(RoadEdge(len(edges), tail, head, length, way.osm_id))
                edges.append(RoadEdge(len(edges), head, tail, length, way.osm_id))
        return cls({i: xy for xy, i in node_ids.items()}, tuple(edges))

    def nearest_node(self, lon: float, lat: float) -> int:
        return min(self.node_xy, key=lambda n: _distance_m((lon, lat), self.node_xy[n]))

    def shortest_path_edges(
        self, origin: int, destination: int, banned: frozenset[int] = frozenset()
    ) -> list[int] | None:
        """The edge ids of the shortest route by length, or None. This is a plain static search."""
        best = {origin: 0.0}
        via: dict[int, RoadEdge] = {}
        queue = [(0.0, origin)]
        while queue:
            dist, node = heapq.heappop(queue)
            if dist > best[node]:
                continue
            if node == destination:
                break
            for e in self._out.get(node, []):
                if e.id in banned:
                    continue
                if dist + e.length_m < best.get(e.head, float("inf")):
                    best[e.head] = dist + e.length_m
                    via[e.head] = e
                    heapq.heappush(queue, (best[e.head], e.head))
        if destination not in best:
            return None
        path = []
        node = destination
        while node != origin:
            path.append(via[node].id)
            node = via[node].tail
        return path[::-1]

    def graph(self, speed_mps: float) -> Graph:
        return Graph(Edge(e.id, e.tail, e.head, e.length_m / speed_mps) for e in self.edges)
