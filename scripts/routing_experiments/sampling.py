"""The pair sampler of the routing experiments (US-091).

Origins and destinations are drawn uniformly inside the model border (.claude/CLAUDE.md, "Test points stay inside
the model border") and kept until each length class is full. The class is set by the straight-line distance,
because the route length is not known before the route is planned. Seeded, so a run can be repeated.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000.0
LENGTH_CLASSES = ("under_2km", "2_to_5km", "over_5km")


@dataclass(frozen=True)
class Border:
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float


BORDER = Border(105.7015, 105.7971, 20.9754, 21.0269)

LonLat = tuple[float, float]


@dataclass(frozen=True)
class Pair:
    name: str
    length_class: str
    origin: LonLat
    destination: LonLat

    def to_json(self) -> dict:
        return {"name": self.name, "length_class": self.length_class, "from": list(self.origin), "to": list(self.destination)}

    @classmethod
    def from_json(cls, data: dict) -> Pair:
        return cls(data["name"], data["length_class"], tuple(data["from"]), tuple(data["to"]))


def distance_m(a: LonLat, b: LonLat) -> float:
    lon1, lat1, lon2, lat2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(h))


def length_class(meters: float) -> str:
    if meters < 2000:
        return "under_2km"
    return "2_to_5km" if meters <= 5000 else "over_5km"


def sample_pairs(per_class: int, seed: int, border: Border = BORDER, max_draws: int = 1_000_000) -> list[Pair]:
    rng = random.Random(seed)
    found: dict[str, list[Pair]] = {c: [] for c in LENGTH_CLASSES}

    def point() -> LonLat:
        return round(rng.uniform(border.lon_min, border.lon_max), 6), round(rng.uniform(border.lat_min, border.lat_max), 6)

    for _ in range(max_draws):
        if all(len(v) == per_class for v in found.values()):
            break
        a, b = point(), point()
        cls = length_class(distance_m(a, b))
        if len(found[cls]) < per_class:
            found[cls].append(Pair(f"{cls}-{len(found[cls])}", cls, a, b))
    else:
        raise RuntimeError(f"{max_draws} draws did not fill every class: {({c: len(v) for c, v in found.items()})}")
    return [p for c in LENGTH_CLASSES for p in found[c]]
