---
date_drafted: 2026-09-29
type: prd
status: draft
subsystem: airflow-pipeline, floodmap-backend
source_ideas: ["[[sticky-c-lite-routing]]"]
tags: [prd, airflow, graphhopper, raster, depth, edge-id]
related: ["[[time-aware-routing-engine]]", "[[routing-not-time-aware]]", "[[flood-on-roads]]", "[[road-segment-table]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[departure-time-advice-research]]", "[[edge-depth-table-stories]]", "[[sprint-plan-2]]"]
---

# Edge depth table

## Problem

The routing graph needs the flood depth of each GraphHopper edge at each forecast step. No such data
exists today. Depth lives in two other shapes.

- **Per road piece.** `flood_road_values` holds one row per piece per step. `road_segment` cuts pieces per
  OSM way by length, at most 50 m ([[road-segment-table]]). GraphHopper cuts edges at junctions, so pieces
  and edges do not line up one to one.
- **Raster tiles.** `flood_depth_raster_tile` holds every step of every retained run. The depth chart samples
  these along a route, but it returns one mean, maximum, and wet fraction for the whole route, not a depth
  for each road.

Joining a route to `flood_road_values` has no stable key. `flood_forecast.py` says so in its docstring. The
pinned GraphHopper build rejects `osm_way_id` as a path detail (verified on the server, 2026-09-29), so an
OSM way id cannot serve as the key either. The `edge_id` detail does work, and it is exact. The engine in
[[time-aware-routing-engine]] and the "wait until" timeline both need depth by edge id. This PRD builds
the table that gives it to them.

## Goals

1. **Export the graph's edges.** A command lists every edge with its id, its geometry in EPSG:4326, and a hash
   of the graph build. The count equals the graph's edge count.
2. **Build one table for each run.** The table holds one depth value for each edge and forecast step. The
   value is the deepest 1 m sample along the edge, in centimetres, the same statistic as `flood_on_roads`
   (decision D-006). For 20 hand-picked edges, the values equal a direct `ST_Value` reading.
3. **Tag each table with the graph hash.** A reader refuses a table whose hash differs from the loaded
   graph's hash and reports the mismatch.
4. **Publish without a partial read.** A new table becomes visible through one atomic step, and a reader
   never sees a half-written file. The newest 3 runs stay on disk, like the tile table.
5. **Reload without restart.** The engine picks up a new table within 30 seconds, and requests in flight
   finish on the old one.
6. **Two readers, one format.** The Java reader (routing) and the Python reader (the departure timeline)
   both pass the same fixture, which includes a value for every edge and step.
7. **A documented re-import procedure.** After a graph re-import, a person can regenerate the export and the
   table by following the page, and a stale table is detected before it serves a request.

## Non-goals

- **Replacing `flood_road_values`.** It keeps serving `GET /flood/areas` and today's routing.
- **Storing per-vehicle data.** The table holds depth. Each consumer applies its own vehicle limit.
- **Changing the depth chart.** It stays on raster tiles and `POST /flood/forecast`.
- **Enabling `osm_way_id` in the graph.** It is a different route to the same key and needs an image rebuild
  that this work already does for the module. Revisit it only if edge geometry sampling proves wrong.
- **Coverage flags.** An edge with no model coverage reads as depth 0. The user accepted this on 2026-09-29.

## Dependencies and assumptions

1. **Verified, 2026-09-29.** The server's GraphHopper returns `edge_id` and `time` details for a route, and
   `osm_way_id` is not available.
2. **Verified.** `flood_depth_raster_tile` holds tiles of 256 by 256 pixels in EPSG:4326, about 1 m per pixel,
   for every step of the newest 3 runs ([[flood-on-roads]]).
3. **Verified, local database.** The grid-join sampling in `flood_on_roads` reads one step in 1.9 s for 15,285
   pieces and 637,277 samples. Edges total a similar length to the pieces, so a similar time is plausible.
   This is unmeasured for edges and for the server.
4. **Unverified.** GraphHopper has no REST endpoint that dumps edges, so the export needs Java. That makes the
   export depend on the toolchain story in [[time-aware-routing-engine]].
5. **Verified, 2026-10-01.** The graph has 67,833 edges and 51,328 nodes (see "Baselines on the server" in
   [[routing-not-time-aware]]). At 8 steps and 2 bytes, a table is about 1.1 MB per run. The earlier guess of
   2 million edges and 36 MB was about 30 times too high.
6. **Verified, 2026-10-01.** A real run has 8 steps, 15 minutes apart, so the last step is 105 minutes after the
   first. The user stated a 2-hour horizon on 2026-09-29, and no step falls at 120 minutes.
7. **Unverified.** Airflow can reach the volume or bucket that holds the table, and the routing container can
   mount it. The blocker page suggests a volume or MinIO. Choose one in the publish story.
8. **Assumed.** Edge ids change on every graph re-import. The hash exists for that reason.
9. **Server operations.** The same rules as in [[time-aware-routing-engine]] apply to deployment.

## Definition of done

Run each check on the server.

1. **Export.** Given the built graph, when the export command runs, then it writes one row per edge and the
   row count equals the graph's edge count.
2. **Build.** Given a real run and the export, when the Airflow task runs, then one table appears for the run
   with one value per edge and step, and the task reports its duration and file size. The duration is within the build-time limit: the table task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth`.
3. **Spot check.** Given the table, when 20 edges are read against `ST_Value` at their deepest sample, then
   every value matches.
4. **Hash guard.** Given a table built from a different graph, when a reader opens it, then the reader
   refuses it and names both hashes.
5. **Atomic publish.** Given a reader that polls in a loop while the task publishes, when the new table
   appears, then the reader sees the old table or the new one and never a partial file.
6. **Retention.** Given four runs, when the fourth publishes, then the oldest is removed.
7. **Two readers.** Given the shared fixture, when the Java and Python readers read it, then both return the
   same values for every edge and step.
8. **Re-import.** Given a re-imported graph, when the procedure runs, then the export, table, and hash
   change together, and a request that uses the old table is refused before it serves a route.

## Risks and open questions

- **The export needs Java.** The first story that builds the toolchain must land before the export.
- **Build time on the server is unmeasured.** A sampling design that takes 1.9 s per step for pieces could
  take much longer for edges. The proof story measures it. The user set the limit on 2026-10-02: the table task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth`.
- **Graph re-import invalidates the table.** Automatic detection exists, but a stale table means the engine
  falls back to today's model. See [[time-aware-routing-engine]], goal 5.
- **Storage choice is open.** A volume is simpler. MinIO gives one place for all runs. Decide in the publish
  story.
- **Open question.** Does the DAG wait for this task, or does the task run after the routing tasks without
  blocking them? The stories assume it does not block, because the engine has a fallback.

## Decisions

| Date | Question | Decision | Why |
| ---- | -------- | -------- | --- |
| 2026-09-29 | What key joins depth to the route? | GraphHopper `edge_id` | It is exact and the `edge_id` detail is available. `osm_way_id` is not. |
| 2026-09-29 | What statistic per edge? | The deepest 1 m sample | Matches D-006 and `flood_on_roads`, and is the cautious choice. |
| 2026-09-29 | Does the table store vehicle limits? | No | Consumers apply their own limit. |
| 2026-09-29 | Is coverage flagged? | No. No coverage reads as 0 | Stated by the user. |
| 2026-09-29 | Who reads the table? | The Java engine and the Python departure timeline | The user chose option C for the timeline. |
| 2026-10-02 | What build-time limit? | The table task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth` | The user accepted this suggestion. A run has 15 minutes, and the tile task alone took up to 11.5 minutes under the old 50 mm/h storm (`US-065`). |

## Rollback

- Stop the Airflow task. Existing tables stay on disk and nothing else changes.
- Delete the table files. The engine falls back to today's model and the response carries the flag.
- `flood_road_values` and the raster tiles are untouched throughout.

## Status history

- **2026-09-29, draft.** Written from [[sticky-c-lite-routing]]. Stories are in [[edge-depth-table-stories]].
- **2026-10-01, draft.** Assumptions 5 and 6 are verified by `US-046`: 67,833 edges, and 8 steps of 15 minutes. The table is about 1.1 MB per run.
- **2026-10-02, draft.** The user set the build-time limit. The risk, the Definition of done (item 2), and the Decisions table follow. The gate on `US-045` is cleared.
- **2026-10-05.** Task 9c ran over 770 s in one sampling step under the replay. Blocker [[9c-sampling-step-runs-over-770-seconds]], fix `US-070` (`ANALYZE` first, 120 s step limit). The 5-minute limit stays unproven under load until `US-045` reads the next 9c logs.
