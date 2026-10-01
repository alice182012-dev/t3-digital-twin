"""Run the four synthetic flood scenarios on a real road corridor and print the result of each.

Usage: python3 run_scenarios.py ROADS_GEOJSON ORIGIN_LAT ORIGIN_LON DEST_LAT DEST_LON
Story R2 (US-047). The roads file is a GeoJSON file of OSM ways, for example
marie-curie/raster-first/roads.geojson. Keep both points inside the 3Di model border (.claude/CLAUDE.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

from corridor import RoadNetwork, load_ways
from scenarios import SCENARIOS, VEHICLE_LIMIT_CM, run_scenario


def main(argv: list[str]) -> int:
    roads, o_lat, o_lon, d_lat, d_lon = argv[0], *map(float, argv[1:5])
    network = RoadNetwork.from_ways(load_ways(Path(roads)))
    origin, destination = network.nearest_node(o_lon, o_lat), network.nearest_node(d_lon, d_lat)
    print(f"{len(network.edges)} directed edges, {len(network.node_xy)} nodes")

    print(f"{'scenario':<27}{'vehicle':<10}{'detour':<8}{'expected':<10}{'observed':<10}{'crossed':<9}{'plain route crosses':<20}ok")
    outcomes = []
    for scenario in SCENARIOS:
        for vehicle, limit in VEHICLE_LIMIT_CM.items():
            for with_detour in (True, False):
                o = run_scenario(network, origin, destination, scenario, limit, with_detour)
                outcomes.append(o)
                print(
                    f"{scenario.name:<27}{vehicle:<10}{'yes' if with_detour else 'no':<8}{o.expected:<10}{o.observed:<10}"
                    f"{len(o.crossings):<9}{len(o.static_crossings):<20}{'yes' if o.matches_sticky_column else 'NO'}"
                )
    first = outcomes[0]
    print(f"route: {first.path_edges} edges, {first.path_length_m:.0f} m. Corridor roads: "
          + ", ".join(f"{s.name.split('.')[0]} {next(o for o in outcomes if o.scenario is s).corridor_way_id}" for s in SCENARIOS))
    matched = sum(o.matches_sticky_column for o in outcomes)
    print(f"{matched} of {len(outcomes)} match the sticky column. Crossings on returned routes: {sum(len(o.crossings) for o in outcomes)}.")
    print(f"The plain shortest route crosses a closed road in {sum(bool(o.static_crossings) for o in outcomes)} of {len(outcomes)} runs.")
    return 0 if matched == len(outcomes) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
