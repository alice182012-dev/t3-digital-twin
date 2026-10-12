---
date_drafted: 2026-10-12
type: user-story
us_id: "US-116"
title: "Let a run with no wet road piece win the winner query"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Reviewed
kind: bug
priority: P1
estimate: S
sprint: 
subsystem: routing, backend
source_ideas: []
related: ["[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]", "[[flood-on-roads]]", "[[decision-log|D-036]]"]
tags: [user-story]
---

# US-116 Let a run with no wet road piece win the winner query

As a driver, I want the map and the route fallback to show no water when the newest run has none, so I am not routed around roads that have dried.

A run in which no road piece is wet writes no rows to `flood_road_values`.
The winner query in `floodmap/graphhopper-flood-road/backend/flood_areas.py` picks the newest run that has rows at a forecast time, so an older run that still has water wins.

Given a newest run with no wet piece and an older run that is wet at the same forecast time, when `/flood/areas` is read for that time, then the response has no features.
Given the same state, when `/route` falls back to the legacy custom model, then it has no flood areas.
Given a newest run that is wet at some time, then the response does not change.

The method is decided in [[decision-log|D-038]].
The run registry `flood_road_file` gets a column for the run's forecast times, written when `flood_on_roads` registers the run, and the winner picks the newest registry run that covers the forecast time.
The fix is needed in both plans: the edge table of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] keeps the same registry, so the work is not thrown away when `flood_road_values` is deleted.
The server had no run with `feature_count` 0 among 75 runs on 2026-10-12, so a test needs a constructed dry run.

Dependencies: the owner accepts [[decision-log|D-038]].

## Status history

- **2026-10-12, draft.** Found at Sprint 13 planning. It stays in the backlog until the spike decides the method, so the fix is not thrown away.
- **2026-10-12, In progress.** Started after the owner accepted [[decision-log|D-038]]. Reproduced on a throwaway PostGIS (`imresamu/postgis:17-3.5`, on the server, reached through a tunnel) with the real `flood_on_roads` writer and the real backend: an older wet run (`20260924T164803`) and a newer dry run (`20260924T170303`) that overlap at local 17:03:03. `GET /flood/areas?valid_time=2026-09-24T17:03:03` returned 1 `b4` feature from the older run, where the newest run is dry. The time 16:48:03, which only the older run covers, returned the same feature, and 17:18:03 returned none.
- **2026-10-12, Reviewed.** Fixed on `modular`, pushed, and deployed on the server, with the checks in details items 10 to 13. It waits for the server screenshot and the owner's acceptance.

## Evidence and details

**Evidence:** the reproduction and the fix, run on a throwaway PostGIS (`imresamu/postgis:17-3.5`, removed afterwards) with the real `flood_on_roads` writer and the real backend. No server screenshot yet, because nothing is deployed.

**Details:**

1. Root cause: the winner query took the newest `timestamp` that has rows in `flood_road_values`, and a run with no wet road piece has no rows. The registry `flood_road_file` held the run but not the forecast times it covers.
2. `flood_road_file` has a new column `forecast_times` (`TIMESTAMP[]`, naive Vietnam local time). `create_flood_road_tables.py` adds it and backfills existing runs from their rows. `flood_on_roads.compute` writes it for every run, including a dry run.
3. `_WINNER_SEG_SQL` in `flood_areas.py` picks the newest registered run whose `forecast_times` contains the requested time and reads that run's rows. A winner with no rows gives no features. The pinned-run query did not change. There is one source for the winner and no union with `flood_road_values`.
4. A shadow run (`flood_on_roads.py --target`) registers no times, and its conflict update keeps the stored times. Without this, a shadow run would have won times with no rows and blanked the overlay.
5. Same three requests on the same seed, `GET /flood/areas` with `run=latest`. At 17:03:03, where the newest run is dry, the answer changed from 1 `b4` feature to 0. At 16:48:03, which only the older run covers, it stays 1 `b4`. At 17:18:03 it is 0. A request pinned to the older run still returns its `b4` feature.
6. The tests that failed first on the old code now pass: `test_flood_areas.py` (script, prints `ok`), `test_server.py` (script, prints `ok`), 26 in `scripts/flood_roads`, 12 in `scripts/test_standing_flood.py`, and 21 contract tests. The fixture of `test_server.py` registers its run with its forecast time, because its routing tests would otherwise get no areas.
7. The backend connects as `routing_reader`, which can read only the tables on the contract page, so `flood_road_file` was added to [[core-output-contract]] (a seventh table, with the `routing_reader` list), and `test_core_contract.py` follows. Deploy order on the server: first run `create_flood_road_tables.py` (the column and the backfill), then run `create_routing_reader_role.py routing_reader` again, then restart `floodmap-backend`. A backend that starts before the first step fails `/flood/areas` on the missing column.
8. `prune_flood_road_values.py` is not changed. It builds its run list from `flood_road_values`, so it never deletes the registry row of a dry run. Those rows stay, and an old row covers only past times.
9. For [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]]: the run registry moves with the new table, and [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] deletes `flood_road_file` after the readers have moved.
10. Deployed on the server on 2026-10-12, in the order of item 7, with the owner's go. `modular` was pushed (`b370a09` to `d100d6e`) and pulled on the server by fast-forward. `create_flood_road_tables.py` ran in the worker: `flood_road_file` went from no `forecast_times` column to 75 of 75 runs backfilled, with 8 forecast times each (2026-10-11 00:15 to 02:00 for the newest). `create_routing_reader_role.py routing_reader` ran from a temporary copy in the worker (removed afterwards) and printed that the role reads `flood_road_file` among its 7 tables.
11. Checked as `routing_reader` on the server: `SELECT` on `flood_road_file` returns 75 runs with 75 `forecast_times`, and a `DELETE` is refused with "permission denied". The new winner rule gives the same run as the old rule for all 99 forecast times that have rows, and no registry run is without rows, so the server has no dry run to show the difference.
12. The owner rebuilt the image of `floodmap-backend` from the server desktop on 2026-10-12 (the container was created at 12:11 +07). The new `flood_areas.py` is in the image, `/health` reports PostGIS and GraphHopper up, the container runs as `routing_reader`, and the log has no error.
13. Checked on the server, `GET /flood/areas` inside the container, `run=latest` against the same run pinned. Two runs cover the times 00:15 to 01:45 of 2026-10-11: `2026-10-11T00:00:00` and `2026-10-11T00:15:00`. For the 6 times that both cover (00:15 to 01:30) and both vehicles, 12 requests in all, the answer for `latest` equals the answer for the newest run, by feature count and by a hash of the geometry. The two runs differ at 00:45 for the motorbike (374 against 373 features), at 01:15 for both vehicles, and at 01:30 for both vehicles, so `latest` is the newest run there and not the older one. 0 mismatches. A time that no run covers (2026-10-12 09:00) returns 0 features.
14. Not shown on the server: a dry newest run, because the server has none and the check does not write to its tables. The dry case is shown by the reproduction on the throwaway PostGIS (item 5).
15. Open for `Done`: the server screenshot of the checks in items 11 and 13, and the owner's acceptance. The command is `bash artifacts/docs/stories/evidence/us-116-server-check.sh` from the Mac. It is read-only, and the screenshot goes to `artifacts/docs/stories/evidence/us-116-server-check-output.png`.
