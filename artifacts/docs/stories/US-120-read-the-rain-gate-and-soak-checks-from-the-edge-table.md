---
date_drafted: 2026-10-12
type: user-story
us_id: "US-120"
title: "Read the rain gate and the soak checks from the edge table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Done
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-120 Read the rain gate and the soak checks from the edge table

As the owner of the pipeline, I want the rain gate and the soak checks to read the edge table, so no job reads `flood_road_values` any more except the ones still to be moved.

`standing_flood.py` reads the maximum depth of the newest runs from `flood_road_file` and `flood_road_values`, and `soak_checks.py` picks roads whose depth lies between two vehicle limits.
The story moves both to the table and the registry of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]].

Given the newest 5 runs with a dry run among them, when the gate reads them, then the dry run counts as dry, and the result equals today's result on the same runs.
Given the soak `roads` check, then it picks edges between the two limits from the new table, and each pick routes on the server.

Dependencies: [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is `Done`.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.
- **2026-10-12, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: its dependencies are `Done` or in the same sprint, and its acceptance check is written.
- **2026-10-12, Reviewed.** Built and tested, not deployed, because the server was unreachable (SSH to port 22 timed out). `standing_flood.py` counts dry runs from `edge_depth_run` and `edge_depth`, and a run with no wet edge counts as dry at 0 cm. The soak `roads` check picks edges between the two limits from `edge_depth` and `graph_edge`. It finds the neighbours of an edge from `edge_key` (`<way>:<position>`) and converts the forecast time from local time to UTC. 17 tests of `test_standing_flood.py` and 43 of `test_soak_checks.py` pass against a throwaway PostGIS, and the reader tests caught a real defect (`to_regclass('public.…')` hid the table outside `public`). One difference is known. `edge_depth` holds whole centimetres rounded to the nearest, so a run whose deepest edge is 4.5 to 4.99 cm now counts as wet, where the old gate counted it dry. Still open: the gate result on the same runs as the old gate, the soak picks routing on the server, and the server screenshot.
- **2026-10-13, Done.** The product owner accepted it after the server check. The evidence is the screenshot `US-120-server-soak-roads-2026-10-13.png`. The `blocked` pairs of the soak check were all skipped (details item 4), and the owner accepted the story with that limit.

## Evidence and details

**Evidence:** `artifacts/docs/stories/evidence/US-120-server-soak-roads-2026-10-13.png`, the run of `soak_checks.py roads --per-bucket 12` inside `airflow_new-floodmap-backend-1`.

**Details:**

1. The rain gate reads the edge table.
   On the two stored storm runs, the old reading and the new one agree: both runs are wet, because both deepest values are far above the 5 cm limit.
   Run `20261010T223000` has a deepest value of 4.39 m in `flood_road_values` and 4.21 m in `edge_depth`.
   Run `20261011T001500` has 3.49 m and 3.32 m.
   The two tables measure a piece and an edge, so the values differ.
2. Both stored runs are wet, so no dry run was compared.
   The known difference for a deepest value between 4.5 and 4.99 cm was not tested on data.
3. The task `0_check_forecast_rain` read the standing flood on the server and answered `chain_ended`, with 0 of 5 dry runs in a row and the newest run 968.6 minutes old.
4. The first soak run on the server failed one pair, a motorbike on edge `601917327:1`.
   The check had picked the edge at 22 cm in run `20261010T223000` (15:30 UTC), above the motorbike limit of 20 cm.
   With `TIME_AWARE_ROUTING` on, the engine ignores the `run` and `valid_time` of a request.
   It answered `td.status: unknown` and judged run `20261011T001500` at 19:00 UTC, where the edge reads 19 cm, so the route crossed it.
   This was a fault of the check, not of the routing.
5. The check now sends one probe route, reads `td.run` and `td.departure` from the hints, and picks edges at that step (`engine_cell` and `probe_engine_cell` in `scripts/backend_soak/soak_checks.py`).
   Five new tests of `EngineCellTest` pass, and 13 tests pass without a database.
   The change is the commit "Check the cell the time-aware engine judges in the soak roads check".
6. Result after the change, with a temporary `LIVE` row in `forecast_mode` because `DEMO` switches the engine off:
   26 roads and 104 pairs, run `20261011T001500` at 19:00 UTC.
   28 `found` pairs and 14 `crosses` pairs passed, 11 `crosses` pairs and 51 `blocked` pairs were skipped, 0 failed, and there were 0 server errors.
7. Limit: all 51 `blocked` pairs were skipped, because the dry control route does not cross the picked edge.
   This run shows no kept `blocked` promise.
   The check of 2026-10-02 on `flood_road_values` held all 40 of its `blocked` promises.
   A check that picks pairs whose dry route must cross the edge is not a story yet.

