---
date: 2026-10-01
type: concept
status: active
tags: [routing, sticky-c-lite, reference, checker, sprint-5]
related: ["[[time-aware-routing-engine]]", "[[time-aware-routing-engine-stories]]", "[[routing-not-time-aware]]", "[[edge-depth-table-format]]", "[[sprint-plan-2]]", "[[routing-depth-threshold-model]]", "[[graphhopper-backend]]"]
last_updated: 2026-10-09
---

# Sticky routing reference and checker

The reference is a slow, readable implementation of sticky C-lite routing. The checker re-walks a route and lists every road it entered while closed. The fast engine (`US-050`) is compared against the reference, and the server proof (`US-055`) uses the checker on the routes that `POST /route` returns. The requirements are goal 1 of [[time-aware-routing-engine]], and the story is `US-047` ([[time-aware-routing-engine-stories]] Story R2).

The code is in `scripts/routing_reference/`, with tests beside it. It is pure Python with no database and no GraphHopper.

## The closure rule

`StickyClosure.closing_step(edge_id, arrival_s)` returns the first forecast step whose time lies in `[departure, arrival + margin]` and whose depth is at or above the vehicle's limit. A road is closed for that arrival when a step exists.

- The depth limits are in `VEHICLE_LIMIT_CM`: `motorbike` 20 cm and `car` 30 cm. A test fails if they differ from `threshold_cm` in `flood_utils.py`. A depth equal to the limit closes the road, as band `b4` does in `flood_utils.py`.
- The margin is 600 s (`DEFAULT_MARGIN_S`), the 10 minutes of the PRD.
- The end of the window is included. A step exactly at `arrival + margin` closes the road.
- Steps before the departure are ignored. This is the "sticky from the departure" wording, which the user confirmed for `US-050` on 2026-10-02. Water that drained before departure does not close a road.
- Closures only grow as the arrival time grows. An earlier arrival is never worse, so a Dijkstra search over arrival times is exact without any waiting.

## Functions

| Name | What it does |
| ---- | ------------ |
| `earliest_arrival(graph, origin, destination, rule)` | Returns the route that reaches the destination first without entering a closed road, or `None`. The search ranks by travel time and ignores the depth-band cost factors of the engine. |
| `find_crossings(edge_ids, edge_seconds, rule)` | Walks a route from the departure time, adds each edge's travel time, and returns a `Crossing` for every edge that was closed on entry. |
| `RoadNetwork.from_ways(ways)` | Builds a road network from OSM ways. A vertex shared by two ways, or a way's end, is a node. Each road piece has a forward edge `2k` and a reverse edge `2k + 1`. One-way tags are ignored. |
| `run_scenario(...)` | Runs one of the four scenarios on a network and returns an `Outcome`. |

To check a GraphHopper route, take the `edge_id` path detail as `edge_ids` and the `time` path detail divided by 1000 as `edge_seconds`. The edge ids must be the ids of the table's graph build ([[edge-depth-table-format]]).

## The scenarios

`SCENARIOS` in `scenarios.py` holds the four rows of the test table in [[routing-not-time-aware]], with the result of the sticky column. A scenario floods one road of the route and sets the traveller's speed so the road is entered at exactly the table's minute. A scenario has the 8 steps of a real run, 15 minutes apart, so the last step is 105 minutes after the first ([[routing-not-time-aware]], "Baselines on the server"). The flood depth is 50 cm by default.

Each scenario runs for `motorbike` and `car`, with a detour and without one. With a detour, a blocked scenario must route around the road. Without one, it must return no route. A scenario that passes must use the road in both cases. The returned route must also have no crossing.

## Run it

```bash
cd scripts/routing_reference
python3 -m pytest -q
python3 run_scenarios.py ../../marie-curie/raster-first/roads.geojson 21.0250 105.7550 21.0255 105.7620
```

The arguments after the roads file are the origin latitude and longitude, then the destination latitude and longitude. Keep both points inside the model border (`.claude/CLAUDE.md`).

## Measured

On 2026-10-01 the pair above gives a route of 15 edges and 1,488 m on `roads.geojson` (47,210 directed edges). All 16 runs match the sticky column and the returned routes have no crossing. The plain shortest route, which ignores time, crosses a closed road in the 8 blocked runs. The search agrees with an exhaustive search over all simple paths on 300 random graphs.

## Open items

- `scripts/routing_experiments/real_graph.py` builds the `Graph` of the real network from the format-2 export (`edge_id,wkt,base_node,adj_node`). Each road is open in both directions and its travel time is its length at 30 km/h, because the export has no one-way flag or speed. A smoke sweep ran on the server export on 2026-10-09.
- The scenarios use a synthetic depth per edge. They do not read a real depth table. `US-045` proves the real table on the server.
- The Java engine of `US-050` passes the same four scenarios on a hand-built corridor (`ScenarioReport`, and its random-graph test against an exhaustive search), but the reference and the engine have not yet been compared on real Hanoi roads. That is `US-055`.
- The wording "sticky from the departure" waits for the user's confirmation before Sprint 8.
- The story named a throwaway PostGIS database. The scenarios need no spatial query, so none is used.
