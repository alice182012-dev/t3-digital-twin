---
date_drafted: 2026-10-12
type: user-story
us_id: "US-119"
title: "Read the map overlay and the route fallback from the edge table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: In progress
kind: story
priority: P1
estimate: S
sprint: 
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-119 Read the map overlay and the route fallback from the edge table

As a driver, I want the map overlay and the route fallback to read the same water as the routing engine, so the map never shows a road that the router treats differently.

`flood_areas.py` (`/flood/areas`) and the legacy custom model of `/route` read `flood_road_values` through `_WINNER_SEG_SQL`.
The story moves both to the edge table of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]]. The winner is the newest registry run that covers the forecast time, and the geometry comes from `graph_edge`.

Given a newest run with no wet edge and an older wet run at the same time, when `/flood/areas` is read, then the response has no features.
Given a newest run that is wet, then the response has the same wet roads as the engine's table for that run, and the depth bands match to the centimetre.
Given the same request before and after the move on one replay run, then the story records the difference in the overlay area, which comes from the edge grain.

Dependencies: [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is `Done`.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.
- **2026-10-12, In progress.** Started on the owner's request, outside the sprint plan, so it has no `sprint`. [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is built and its tables exist on the server, but they hold no rows until the next real `9c` run. The change is in `flood_areas.py`, which serves both `/flood/areas` and the legacy custom model of `/route`. Built and tested on a throwaway PostGIS, not deployed. Still open: the deploy, the reader role rerun, the before and after comparison on one replay run, and the server screenshot.
- **2026-10-12, In progress.** Pushed and pulled on the server (head `cf640a2`, `--ff-only` from `alice`). The role `routing_reader` got `SELECT` on `edge_depth` and `edge_depth_run` with two `GRANT` statements, because the worker does not mount the backend module or the contract page that `create_routing_reader_role.py` needs. `build_edge_depth.py` wrote live rows for the stored storm runs `20261010T223000` and `20261011T001500` into a scratch output folder, without `--publish`, so `latest` did not move. The old and new `derive_areas` were compared on live data as `routing_reader` (details item 6). The `floodmap-backend` image is not rebuilt yet, because `docker build` fails over SSH, so the running backend still reads `flood_road_values`.

## Evidence and details

Fill this when the story reaches `Done`.

Details so far:

1. One query now serves both reads. `_SEG_SQL` takes the winner from `edge_depth_run` (`_LATEST_WINNER`) or the pinned run (`_PINNED_WINNER`), joins `edge_depth` to `graph_edge` on `edge_key`, and builds the same buffered bands as before.
2. Two units differ from `flood_road_values`. Depth is whole centimetres, so a band limit is `round(limit_m * 100)` and 15 cm is in band `b3` while 14 cm is in `b2`. The table holds UTC, so `_utc_naive` turns the request's `valid_time` into UTC, and a time with no offset is read as Vietnam local time, as before.
3. `test_flood_areas.py` (against PostGIS) covers the three criteria that need no live run: a newest dry run hides an older wet run, a wet newest run answers with its own edges, and the centimetre limits. `test_server.py` covers `/flood/areas` and `/route` over HTTP. `test_server.py` failed before this story on a missing `flood_run_output` table, and the fixture now creates it.
4. The core output contract page now describes `edge_depth` and `edge_depth_run`, and `routing_reader` lists them. It still lists `flood_road_file` and `flood_road_values`, so a rollback to the older backend keeps working. [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] removes them.
5. Deploy order: roll out the backend, then run `create_routing_reader_role.py routing_reader` so the role can read the new tables. Until the first `9c` run writes rows, a `latest` request returns no features.
6. The overlay on live data, run `20261010T223000`, from `marie-curie/us-119/compare.py` as `routing_reader`. The new overlay covers about 2.2 times the area of the old one for motorbike and about 2.4 times for car, at every one of the 8 steps. At 22:30 +07, motorbike: 619 features and 2.85 km2 before, 580 features and 6.29 km2 after. Car: 472 and 2.10 km2 before, 468 and 4.98 km2 after. The cause is the edge grain. At that step, with a depth of 20 cm or more, the wet edges are 766 with 84.8 km of length (111 m each), and the old wet road pieces are 601 with 24.9 km (41 m each). An edge is drawn whole when any sample along it is wet, and 62.7 km of the new wet length lies outside a 2 m buffer of the old pieces. In the other direction, 3.3 km of old pieces lie outside a 2 m buffer of the new edges. This difference is what the engine already sees, since `9c` builds its table from the same edges.
