---
date: 2026-10-08
last_updated: 2026-10-13
type: reference
status: draft
tags: [paper, arxiv, handoff, routing, system]
related: ["[[T3-Digital-Twin_Architecture]]", "[[sticky-c-lite-routing]]", "[[sticky-closure-proof]]", "[[sticky-routing-reference]]", "[[3di-simulation-orchestration]]", "[[core-output-contract]]", "[[edge-depth-table-format]]", "[[timescaledb-schema]]", "[[flood-metric-extractor]]", "[[graphhopper-backend]]", "[[graph-reimport-procedure]]", "[[test-dataset]]", "[[analysis-service]]", "[[decision-log]]", "[[EP-20-routing-paper-experiments|EP-20]]", "[[EP-22-keep-a-real-storm-as-the-test-dataset|EP-22]]", "[[SPR-014-finish-the-remaining-backend|SPR-014]]", "[[flood-map-reaction-time-findings]]"]
---

# Handoff for two arXiv papers: flood routing and the end-to-end system

This page is the brief for the agent that writes two papers about the t3-digital-twin project.
It maps every claim to the file that backs it.
It says which results exist, which are pending, and which the agent must never state as fact.

Written 2026-10-08 and brought up to date on 2026-10-13, on branch `modular`.
Everything here is a pointer.
The agent reads the cited files and checks each number against its source before using it.

## The two papers

| | Paper A, routing | Paper B, end-to-end system |
| --- | --- | --- |
| Working title | Time-aware flood routing with sticky closure on forecast depth | A 15-minute flood digital twin for Hanoi: from rain forecast to vehicle-aware routes |
| One claim to remember | A route planned on forecast depth stays safe on arrival. Sticky closure keeps the search a forward time-dependent Dijkstra, so it is exact for the sticky rule. The reference search costs the same order as a static search, and the engine search has no proven polynomial bound (see "Claims the papers must not make"). | A 3Di-based digital twin can publish flood depth, map tiles, and a routing input every 15 minutes, on one server, from an operational rain forecast. |
| Kind | Algorithm and measurement | Systems and engineering experience |
| Suggested arXiv primary | cs.DS, cross-list cs.CY and cs.AI | cs.DC, cross-list cs.DB |
| Why those | The proof and complexity argument are computing-core. | Pipeline, storage, and scheduling are computing-core. |

The author is applying to a computing master's program.
Keep both papers in computing categories.
Do not put either in physics.geo-ph or a hydrology category.
The hydrology is the setting, not the contribution.

A first-time arXiv submitter needs an endorsement in the chosen category.
Raise this with the author before the writing is done.

## Rules for the agent

1. Paper text is research writing. Invoke the research-writing skills from the user's global instructions first: `research-writing-assistant:using-research-writing`, then `paper-orchestration`, `evidence-driven-writing` with `literature-review` for the Introduction and Related Work, `experiment-results-planning` for Results, `writing-chapters` with `writing-core`, and `peer-review` before calling a section ready. Do not use `pstack:technical-writing`, `pstack:unslop`, or `pstack:poteto-mode` on paper text.
2. Write nothing from memory. Open the cited file and quote its number. The vault says which facts are verified and which are marked unverified. Keep that distinction.
3. Mark any missing result as a placeholder, for example `[RESULT: violation rate, Question 1]`. Never invent a number.
4. Do not edit anything under `artifacts/raw/`. It is read-only.
5. `marie-curie/` is untracked scratch space and can be deleted at any time. Copy what a paper needs (tables, bibliography, result files) into a new folder, for example `papers/`, before relying on it. Ask the author before creating that folder.
6. Name the providers: 3Di, GraphHopper, Tomorrow.io (the live rain forecast, D-013 in the decision log), and NASA IMERG (the offline storm replay). Do not name NCHMF as a data source. The original design used it, and NCHMF did not approve API access. The 15-minute cycle is approved (D-014).
7. Read the story status before you call a feature built or verified. `Done` means the product owner accepted it after the check in the environment the story names. `Reviewed` means built and tested but not deployed and not accepted. A `Reviewed` feature is not a server result. Name it as built, awaiting the server check. The section "Built and not yet checked on the server" lists the current ones.

## Claims the papers must not make

These come from the vault's own caveats.

- Name the storm behind every result. The replays are the real 2026-09-16 Hanoi event (NASA IMERG rain, `marie-curie/us-088/hanoi_20260916_storm.csv`, also kept as `scripts/rain_events/hanoi_20260916_storm.csv`), so they are not synthetic. The earlier constant 50 mm/h storm is synthetic. The reviewer-questions note (`marie-curie/idea-routing-paper-reviewer-questions.md`, Question 1 threats) was written on 2026-10-02 before any replay existed, so its "synthetic" wording applies only to the 50 mm/h storm.
- Even on the real event, depths are 3Di model output, not observed depths. A violation rate is a rate in the model driven by real rain. Do not present it as a measured rate of drivers meeting closed roads. The flood model is not validated in this project (D-021, `EP-20`).
- The vehicle depth limits (motorbike 20 cm, car 30, truck 35, foot 40) have one owner, `VEHICLE_PROFILES` in `floodmap/graphhopper-flood-road/scripts/flood_utils.py` ([[US-074-give-the-vehicle-thresholds-one-owner|US-074]]). They are policy parameters. A source search on 2026-10-08 (`marie-curie/vehicle-limit-sources.md`, copy it first) found this support. Never call a threshold safe.
  - Car 30 cm is supported for a small passenger car by Shand et al. 2011 and the Australian AIDR guidance (both 0.3 m). UK guidance gives 0.5 m for most cars and vans.
  - Motorbike 20 cm is partly supported. The best source is Ho Chi Minh City police guidance reported by Thanh Niên on 2026-10-06 (care below about 15 cm, do not push on at 20 to 30 cm). No peer-reviewed motorbike stall experiment exists. Do not cite the Vu 2024 report for the limit, because it could not be opened.
  - Truck 35 cm has no source. Shand lists commercial vehicles as a data gap. Call it an assumption.
  - Foot 40 cm is partly supported. It sits below the Cox 2010 depth caps (0.5 m for children, 1.2 m for adults), which the search read only through a secondary report. No source gives 40 cm, and the literature ties depth to velocity.
  - Experiment P5 is replaced by this search. P3 (sensitivity, [[US-092-test-how-the-vehicle-limits-change-the|US-092]]) is the main defense of the limits.
- The app's recommended route uses a precaution depth of 50 percent of each limit (motorbike 10 cm, car 15, truck 17.5, foot 20), and the hard-limit route is a second option flagged as passing through water ([[decision-log|D-021]], [[US-097-recommend-a-route-that-avoids-the-precaution|US-097]]). The 50 percent is a policy parameter, set because the flood model is not validated. The sweep of the fraction is in `US-092`. The route panel for the two paths is not built ([[US-098-show-the-recommended-route-and-the-through|US-098]], `Not started`).
- Sticky closure is conservative. A road that drained stays closed for a traveller who arrives after it drained. It is exact for the sticky rule, not for the true arrival-time rule ([[sticky-closure-proof]], Part 6). The product owner kept this rule on purpose to protect the vehicle and the person ([[decision-log|D-023]]). The measured price is in [[US-093-measure-how-often-the-sticky-rule-gives|US-093]].
- The written proof exists ([[sticky-closure-proof]], [[US-090-write-the-fifo-lemma-and-the-correctness|US-090]], `Done`). It proves the reference search exact (Theorem 1) and the engine search exact when it runs to the end (Theorem 2). It gives no polynomial bound for the engine's weighted search, so claim the same-order cost only for the reference search, or for the engine when the weight is the travel time. The engine does not use landmarks, and it returns no route if it hits `maxVisitedNodes` or the timeout.
- The 15-minute refresh is not the weakest link for short convective bursts. The rain forecast is. That is an inference in `artifacts/docs/concepts/flood-map-reaction-time-findings.md`, not a measurement. No source gives a measured rate of rise in cm per minute for Hanoi.
- The IMERG area average over the model extent totals 84.95 mm with a peak of 8.73 mm/h, against about 200 mm at the heaviest stations. The replay is gentler than the news reports. Source: `artifacts/logs/2026-10-08.md`, section "US-088".
- The `DEMO` flood is a stored frame of the replayed 2026-09-16 storm, shown when no rain is forecast ([[decision-log|D-030]]). It is not a forecast and not a live result. Do not describe a `DEMO` map, route, or depth as live output. The pinned frame is run `20261011T001500` at 2026-10-10 19:00 UTC, which is built and checked on the server but not accepted ([[US-129-pin-the-peak-step-of-the-demo-flood|US-129]]). In `DEMO` the route skips the time-aware engine ([[decision-log|D-043]]), so a `DEMO` route is no result for Paper A.
- No real-rain result exists for the `results_3di.nc` archive. The mount and the test-rain skip are `Done` ([[US-094-archive-results-3di-nc-and-a-run|US-094]]). The copy, the free-space floor, and the growth need a real forecast above 5 mm/h, and the rain gate stays at 5 mm/h ([[decision-log|D-037]], [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]]).
- `depth_history` holds the model's own forecast values, not observations ([[decision-log|D-028]]). Its rows before the move to `edge_key` were test rain. The server migration of 2026-10-13 deleted them ([[decision-log|D-042]]), and the table now holds only the run loaded since.
- `background_cycle` and the 24-bar histogram were dropped (D-009). Do not describe them as part of the built system.

## Server state

Verified read-only on the server unless a line says otherwise.
Items marked "2026-10-08" were not read again on 2026-10-12 or 2026-10-13.
The server was reachable on 2026-10-13, and the stories of that day hold the evidence.

- The time-aware engine is deployed and was tested on the server on 2026-10-07. On 2026-10-12 the product owner decided that `TIME_AWARE_ROUTING` stays on for `floodmap-backend` ([[decision-log|D-034]]). The read-back at about 10:50 +07 printed `true` in the running container. The flag was set in the server `.env` without `scripts/routing_proof/rollout.ps1`, and no screenshot was taken, so the read-back is the only evidence. The default in `compose.yml` is still `false`.
- With `TIME_AWARE_ROUTING` on, the engine ignores the `run` and `valid_time` of a request. It judges the newest edge depth table at the later of the request time and the clock. A check or an experiment that sends a run and a time to the live backend therefore does not test that step. Read `td.run` and `td.departure` from the route hints to learn the step the engine judged. The soak `roads` check does this since 2026-10-13 ([[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]], details items 4 and 5).
- On 2026-10-13 the owner rebuilt `floodmap-backend`. It now reads `edge_depth` and `graph_edge` instead of `flood_road_values` for the map overlay, the route fallback, the forecast mode, and the pinned step. The tables `forecast_mode` and `demo_pin` exist, `flood_segment_metrics` has an `edge_key` column, and `depth_history` is keyed by `edge_key` ([[decision-log|D-038]]).
- `POST /route` answers from the time-aware engine first. The legacy custom model built from `/flood/areas` runs only when the engine cannot answer ([[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]], details item 7). In forecast mode `DEMO` the route skips the engine ([[decision-log|D-043]]).
- The recorded server proof of 2026-10-07 ([[US-055-prove-the-engine-on-the-server-and|US-055]], `Done`): `compare` changed 37.5% of routes with a median detour of 0.94, `crossings` 0, `departures` 3 of 3 trips, `latency` all 6 cells within 2 times the `US-046` baseline, `scenario-check.sh` 32 of 32. The numbers are in `artifacts/docs/concepts/graphhopper-backend.md`, section "The time-aware search (US-050)". Read the raw outputs from the evidence screenshots before quoting them.
- The pipeline runs four DAGs: `flood_mapping_full`, `routing_adapter`, `flood_tiles` ([[decision-log|D-027]]), and `flood_history` ([[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]]). The cycle is 15 minutes (D-014). The rain forecast is Tomorrow.io (D-013). The rain gate is 5 mm/h, with a rule that keeps simulating while a flood still stands ([[US-101-keep-simulating-while-the-flood-still-stands|US-101]], [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]). The gate and the standing-flood rule read `edge_depth` since 2026-10-13. On the server the owner keeps `flood_mapping_full` paused, so no scheduled run has used the new reads.
- The replay of 2026-10-08 read `hanoi_20260916_storm.csv` with start `2026-10-08T08:45:00Z`, gate 5 mm/h, lookahead 2 hours, simulation duration 7200 s, and worker concurrency 4 (2026-10-08). [CHECK: `compose.yml` defaults worker concurrency to 1 and `SAMPLE_RATE` to 1, and the server `.env` was not re-read.]
- Retention, current values from `core-output-contract.md`, section "Retention": the newest 8 runs for the raster tiles, the polygons, the steps, the MinIO tiles, and the edge depth files (`EDGE_TABLE_KEEP_RUNS`, [[decision-log|D-033]]), and 24 hours for `edge_depth` and `edge_depth_run` (`EDGE_DEPTH_KEEP_HOURS`). `FLOOD_EXTENT_TILE_STEPS` is 2. `flood_road_values` keeps 24 hours ([[decision-log|D-017]]). The five netcdf tables were dropped on 2026-10-10 ([[decision-log|D-022]]).
- The worker still carried variables of the retired GeoJSON chain on 2026-10-08 (`SAMPLE_RATE=20`, `UPDATE_INTERVAL`, `KEEP_LOCAL_GEOJSON`, `VALHALLA_PORT`). The `sample_rate_1_bottleneck` memory note describes that retired chain. Do not cite it as a limit of the current pipeline. Cite the current critical path from `artifacts/archive/plans/us-037-narrow-the-per-run-critical-path.md` instead.

## Built and not yet checked on the server

Two stories are `Reviewed` on 2026-10-13.
Each is built, tested, and checked on the server in part.
The product owner has not accepted either.
Do not present them as accepted server results.
The story holds what each one still needs.

| Story | Built and checked | Still open (from the story) |
| --- | --- | --- |
| [[US-129-pin-the-peak-step-of-the-demo-flood\|US-129]] | Table `demo_pin`, filled by `scripts/database/demo_pin.py`, and every prune keeps the pinned run. On the server it pinned run `20261011T001500` at 2026-10-10 19:00 UTC, with 2,853 wet edges. | The pinned rows and files before and after the prunes, which need a real run of `flood_mapping_full`. The owner's acceptance. |
| [[US-130-serve-the-forecast-mode-and-read-the-pinned-step\|US-130]] | `GET /flood/mode` answers `LIVE`, `PENDING`, and `DEMO` on the server. In `DEMO`, `GET /flood/points`, `GET /flood/areas`, and `POST /route` read the pinned step ([[decision-log\|D-043]]). At 21.01320, 105.76418 the depth is 0.80 m in `DEMO` and 0.10 m in `LIVE` at the first step. | Screenshots of the `LIVE` and `PENDING` answers and of the route comparison. The owner's acceptance. [CHECK: of 10 route pairs between wet edges, 1 routed in `DEMO` and none in `LIVE`. The story did not investigate the cause of the `LIVE` result, so do not read it as a routing result.] |

[[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is `In progress`, not `Reviewed`.
Its code and its two tables are on the server, and task `9c_build_edge_depth_table` wrote 16,370 rows for one run on a hand-made event.
The first `9c` run on a real simulation and the check over 50 consecutive runs are open.

[[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] is `In progress`.
`scripts/testdata/rebuild_tiles.py` rebuilds the depth raster tiles of a stored storm run from its NetCDF, in about 5 minutes per run, and a second call skips the run.
The road-values part is not built.

Accepted on 2026-10-13, after a server check: [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]] (the `forecast_mode` row), [[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]], [[US-121-read-the-flood-metrics-from-the-edge-table|US-121]], and [[US-122-point-depth-history-at-the-edge-table|US-122]].
Their limits matter for any claim.

- `US-111`: the move of a row from `PENDING` to `LIVE` by `9b_load_depth_raster` was not run on the server, because it needs a real run. The DAG tests cover it.
- `US-120`: the soak `roads` check passed 104 pairs with 0 failures, but all 51 `blocked` pairs were skipped. That run shows no kept `blocked` promise.
- `US-121`: the share of closed edges per vehicle is within 2 points of the piece-based share for run `20261010T223000`. The old extractor was not run on that run, and the piece-based numbers come from `flood_road_values`.
- `US-122`: the history holds the one run loaded on 2026-10-13. [[US-113-backfill-per-segment-depth-history|US-113]] (`Ready`) rebuilds the rest.

Accepted earlier: [[US-117-export-a-stable-key-with-each-graph-edge|US-117]] (the stable key, details in "Shared background"), [[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]], and [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]].
`US-119` checked its first criterion, a newest run with no wet edge hiding an older wet run, only against PostGIS, because the server has no such run yet.
`US-117` has the captured output of its server check and no screenshot, which the owner waived at acceptance.

## Results status on 2026-10-13

| Result | Used by | Status | Where it lands |
| --- | --- | --- | --- |
| Rain replay started 2026-10-08 (event `hanoi_20260916_storm.csv`, gate 5 mm/h) | B | Finished. 45 simulating runs in 2 chains, no failed run in either DAG. | `artifacts/logs/2026-10-09.md`, [[US-069-check-the-storage-after-the-48-hour\|US-069]] |
| Storm replay of 2026-10-10, kept as the test dataset (slots 04:00 to 18:15 +07, with the `US-101` fix) | A, B | Finished. `US-102` `Done`. The dataset holds 58 runs (slots 04:00 to 18:15, `US-124`, `D-039`). `US-102` counts 55 of them, from the rain start at 04:45, and the log of 2026-10-11 repeats that 55. | [[US-102-replay-the-storm-with-the-us-101-fix-to\|US-102]], [[test-dataset]], [[decision-log\|D-039]] |
| Edge depth table: edge count, file size, build time (US-045) | B | `Done`. 67,833 edges, 8 steps, 1,085,487 bytes, built in 42.0 s with no other load on 2026-10-05. | [[edge-depth-table-format]], [[US-045-prove-the-table-on-the-server\|US-045]] |
| Task `9c` time inside the DAG, and the cancel rule at 120 s | B | `Done`. `BL-023` `resolved` 2026-10-10. Read the per-run range from the story. | [[US-070-stop-a-slow-sampling-step-from-holding\|US-070]], [[BL-023-9c-sampling-step-runs-over-770-seconds\|BL-023]] |
| Time added by the `edge_depth` row write | B | Measured on 8 stored storm runs, 0.34 to 0.57 s on a build of 45 to 61 s. Not yet seen on a real run. | `US-118`, details item 2 |
| Routing latency within 2 times the `US-046` baseline, and four scenarios times four vehicles pass the checker on the deployed image | A, B | `Done` ([[US-055-prove-the-engine-on-the-server-and\|US-055]]) | `scripts/routing_proof/`, `scripts/routing_reference/scenarios.py` |
| Question 1, violation rate of single-timestep routes | A | `Done` 2026-10-10. Rates by storm stage, vehicle, trip length, and departure step, the live sticky check with 0 crossings under two arrival-step rules, and one labelled sensitivity case. | [[US-091-measure-how-often-a-single-timestep-route\|US-091]] details 3 to 15, [[decision-log\|D-031]] |
| Question 2, sensitivity of the limits and the precaution fraction | A | `Done` 2026-10-10. 30 pairs, one storm, 90 settings. | [[US-092-test-how-the-vehicle-limits-change-the\|US-092]] |
| Question 3, proof | A | `Done`. The written proof. | [[sticky-closure-proof]], `US-090` |
| Question 3, conservatism of sticky against an arrival-only reference | A | `Done` 2026-10-10. `BL-027` `resolved`. The decision to keep sticky is `D-023`. | `US-093`, [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph\|BL-027]] |
| Storage growth over the replay (US-069) | B | `Done` under `D-015`. Hour 6 to hour 12 growth was under the 10 percent pass mark. The hour-6 method is not recorded. | `US-069`, `artifacts/logs/2026-10-10.md` |
| Depth history store and its compression | B | `US-106` `Done`. The compression ratio is 9.7 on the full storm (`US-127`) and 1.7 on one run. The `edge_key` move is on the server (`US-122` `Done`, 20,989 rows over 2,874 edges and 8 moments for one run). The backfill is not (`US-113` `Ready`). | [[timescaledb-schema]], `US-106`, [[US-127-build-the-history-and-metrics-from-the-restored-road-values\|US-127]] |
| Flood tile build as its own DAG, and the two inputs compared | B | `US-103` `Done`. `US-104` `Superseded` after 5 paired runs, and the `postgis` input builds no tiles as shipped. | [[decision-log\|D-027]], [[BL-029-postgis-tile-input-drops-every-polygon\|BL-029]] (`open`) |
| Forecast mode `LIVE`, `PENDING`, `DEMO`, and the pinned demo flood | B | `US-111` `Done`: the `forecast_mode` row is on the server. `US-129` and `US-130` `Reviewed`: the pin and the three modes are checked on the server and not accepted. The frontend banner is `Not started` ([[US-131-show-the-demo-flood-banner-and-the-pinned-frame\|US-131]]). | `D-030`, `D-043` |
| Real-rain archive of `results_3di.nc` and its growth | B | Pending a forecast above 5 mm/h. | `US-114`, `D-037` |
| Edge depth table replaces `flood_road_values` (staged) | B | In progress. `US-116`, `US-117`, `US-119` `Done`. `US-118` `In progress`. `US-120` to `US-122` `Done`. `US-123`, the deletion, is `Ready`. The closed share per vehicle from `edge_depth` is within 2 points of the piece-based share (`US-121`). | [[decision-log\|D-038]], [[SPR-014-finish-the-remaining-backend\|SPR-014]] |
| Test dataset: snapshot, restore, history and metrics from it | B | `US-124`, `US-125`, `US-127` `Done`. `US-126` `In progress` (the tile rebuild is built, the road values are not). `US-128` `Ready`. | [[test-dataset]], [[EP-22-keep-a-real-storm-as-the-test-dataset\|EP-22]] |

Sprint 14 ends 2026-10-25 and holds more points than the forecast ([[decision-log|D-041]]).
Any story not `Done` at that review leaves the sprint, so re-read the story status before the writing starts.

The author chose to hold the writing until the 12-hour replay and the routing experiments had produced numbers.
The replays and the experiments `US-090` to `US-093` are now `Done`.
Re-read this table, `artifacts/TODOS.md`, and the newest logs at the start of the writing job, then update the table.

## Shared background: what the system is

Read in this order.

1. `artifacts/raw/T3-Digital-Twin_Architecture.md` and its working copy `artifacts/docs/concepts/architecture-block-diagram.md`. The raw file is the original design and predates two decisions (vector tiles replaced raster tiles, GraphHopper replaced Valhalla). The concept page marks each component Built or Designed, not built. Describe only what is Built.
2. `artifacts/docs/concepts/3di-simulation-orchestration.md`. The Airflow DAG `dags/flood_mapping_dag.py` (`flood_mapping_full`) runs one cycle every 15 minutes: check the rain forecast, decide whether to simulate, run 3Di, download `results_3di.nc`, compute depth rasters, then publish the depth files and load the depth raster. The tile build leaves for `dags/flood_tiles_dag.py` ([[decision-log|D-027]]). The routing tasks, including `9c_build_edge_depth_table`, run in `dags/routing_adapter_dag.py`, so a routing failure leaves the core run green.
3. `artifacts/docs/concepts/core-output-contract.md`. The eleven PostgreSQL tables, the edge depth files, and the vector tiles that the pipeline publishes. Routing is the first consumer. The page also lists the read-only roles `routing_reader` and `analysis_reader`.
4. `artifacts/docs/concepts/minio-flood-extent-pipeline.md`. Depth raster to polygon tiles in MinIO plus a PostGIS audit copy.
5. `artifacts/docs/concepts/flood-on-roads.md`, `road-segment-table.md`, `flood-metric-extractor.md`, `timescaledb-schema.md`. Depth per road piece and the metrics derived from it. [[decision-log|D-038]] replaces the piece-based tables with the edge depth table, in stages, so check each page against the story status before you describe the current state.
6. `artifacts/docs/concepts/edge-depth-table-format.md` and `core-output-contract.md`, sections `edge_depth` and `edge_depth_run`. Task `9c_build_edge_depth_table` writes the binary file for the engine and, since `US-118`, the wet edges to `edge_depth` with a run registry. A run with no wet edge has a registry row and no depth rows.
7. `artifacts/docs/concepts/graphhopper-backend.md`. The backend in `floodmap/graphhopper-flood-road/backend/server.py`, between the frontend and a pinned GraphHopper. It also holds the forecast mode and the demo step (`flood_mode.py`, `GET /flood/mode`). Since 2026-10-13 it reads `edge_depth` and `graph_edge` for the map overlay, the route fallback, the forecast mode, and the pinned step.
8. `artifacts/docs/concepts/test-dataset.md` and `analysis-service.md`. The kept storm replay and the container for analysis applications.

The edge identity is a stable `edge_key` of the form `<osm_way_id>:<position>`.
`graph_edge.edge_key` carries it, the graph export writes it as a fifth column in format 3, and a graph re-import keeps it when the OSM file is the same ([[US-117-export-a-stable-key-with-each-graph-edge|US-117]], [[graph-reimport-procedure]]).
Before `US-117`, edge ids changed on every re-import.

Hanoi model border for any coordinate used in a figure or test: longitude 105.7015 to 105.7971, latitude 20.9754 to 21.0269 (`.claude/CLAUDE.md`, "Test points stay inside the model border").

## Paper A: routing

### Story the paper tells

1. Before the engine, the backend built one GraphHopper `custom_model` from a single forecast timestep, so every road on a route was judged at one moment. A road that was dry then and flooded in 10 minutes passed. Source: `artifacts/docs/blockers/BL-011-routing-not-time-aware.md` (`resolved`), scenario table. With `TIME_AWARE_ROUTING` on ([[decision-log|D-034]]), the engine plans the route. The single-timestep model is still the fallback and the measured baseline.
2. The design: sticky C-lite. An edge closes for an arrival if any forecast step from the departure to 10 minutes after the entry reaches the vehicle's limit, and it stays closed for the rest of the query. The exact definition, with the margin, is Part 1 of [[sticky-closure-proof]]. Sources: `artifacts/raw/ideas/sticky-c-lite-routing/sticky-c-lite-routing.md`, "Idea" and "Why we choose it", and [[decision-log|D-023]].
3. Why it is exact: with closures that only grow, the arrival function is non-decreasing (FIFO), so waiting never helps and a forward time-dependent Dijkstra is exact. The proof is in [[sticky-closure-proof]] (Parts 2 and 3). The cost claim holds for the reference search, and the engine search has no proven polynomial bound.
4. Why it does not contradict the hardness result: Kleff et al. (SEA 2020) show NP-hardness when waiting is allowed only at dedicated places and closures reopen. Sticky closure forbids reopening inside a query ([[sticky-closure-proof]], Part 6).
5. Two routes per request: the recommended route under the precaution depth, and the route under the hard limit as a second option, flagged when it passes through water ([[decision-log|D-021]]).
6. Evidence: the offline reference and checker, the Java engine compared against the reference, the server proof, and the measured results of `US-091` to `US-093`.

### Design and implementation sources

| Topic | File |
| --- | --- |
| Requirements | The PRDs are archived: `artifacts/archive/prds/PRD-004-time-aware-routing-engine.md`. Each epic now holds its goal and assumptions: [[EP-18-time-aware-routing-engine\|EP-18]] and [[EP-20-routing-paper-experiments\|EP-20]]. |
| Edge depth table requirements and format | `artifacts/archive/prds/PRD-003-edge-depth-table.md`, `artifacts/docs/concepts/edge-depth-table-format.md`, `scripts/edge_depth/edge_depth_table.py` |
| Proof | `artifacts/docs/concepts/sticky-closure-proof.md` |
| Reference implementation and checker | `artifacts/docs/concepts/sticky-routing-reference.md`, `scripts/routing_reference/` (`sticky_reference.py`, `corridor.py`, `scenarios.py`, `run_scenarios.py`, `arrival_only.py`) |
| Experiment harness | `scripts/routing_experiments/` (`experiment.py`, `real_run.py`, `limit_sweep.py`, `precaution.py`, `sticky_cost.py`) |
| Depth to cost model, `DEPTH_BANDS` | `artifacts/docs/concepts/routing-depth-threshold-model.md`, `floodmap/graphhopper-flood-road/backend/flood_areas.py` |
| Stable edge key and graph re-import | `artifacts/docs/concepts/graph-reimport-procedure.md`, [[US-117-export-a-stable-key-with-each-graph-edge\|US-117]] |
| Time-aware route in the backend, two paths, and `DEMO` | `floodmap/graphhopper-flood-road/backend/time_aware_route.py`, [[decision-log\|D-043]] |
| Departure advice ("wait until") | `artifacts/archive/plans/departure-time-advice-research.md`, `route-departures-endpoint.md`, `wait-until-alert.md` |
| Plans and stories | `artifacts/archive/plans/time-aware-weighting-and-search.md`, `time-aware-routing-prds-and-sprint-plan.md`, `engine-server-proof-and-rollout.md`, the archived epics `artifacts/archive/epics/EP-09-time-aware-routing-engine.md`, `EP-08-edge-depth-table.md`, `EP-10-routing-first-consumer.md`, and the current epics `EP-17` and `EP-18` in `artifacts/docs/epics/` |
| Server proof tooling | `scripts/routing_proof/` (`routing_proof.py`, `pairs.json`, `rollout.ps1`), `scripts/backend_soak/` |
| Java engine | `java/` (read its build notes in `artifacts/archive/plans/sprint-6-java-toolchain-and-edge-export.md`) |
| Engine tests | `scripts/routing_reference/test_*.py`, `scripts/routing_experiments/test_*.py`, `floodmap/graphhopper-flood-road/backend/test_core_contract.py` |

### Literature

All in `marie-curie/lit-review-flood-routing/`.
Copy it before use (rule 5).

- `sources.md` is an annotated bibliography with 69 entries, S01 onward. S01 is Kleff et al. 2020, S02 Zeitz 2022, S03 Kaufman and Smith 1993, S05 Orda and Rom 1990, S06 Dean 2004, S17 and S18 Pregnolato 2017 (depth-disruption function), S43 Shand et al. (vehicle stability), S35 Kasmalkar (sensitivity), S48 Manila paper on the Ho Chi Minh City motorbike figure.
- `search-log.md` records 93 searches run on 2026-10-02, with what was found and what was blocked.
- `failed-sources.md` lists sources that could not be opened. Do not cite any of them as read.
- `pdf/` holds the full texts that were opened.
- The finding to build on: time-dependent routing with closures and waiting is established, and flood-aware routing is established. The defensible contribution is the careful combination, the sticky-closure argument, and the measured safety gap. The reviewer-questions note says this directly.

### Experiments

All four planned experiments are `Done` as of 2026-10-10.
The table keeps the original IDs.
The epic is [[EP-20-routing-paper-experiments|EP-20]].

| ID | Story | Experiment | Status and result file |
| --- | --- | --- | --- |
| P1 | [[US-090-write-the-fifo-lemma-and-the-correctness\|US-090]] | The FIFO lemma and the correctness proof of the forward search, the step-boundary cases, and the landmark statement | `Done`. [[sticky-closure-proof]] |
| P2 | [[US-091-measure-how-often-a-single-timestep-route\|US-091]] | Violation rate of single-timestep routes on arrival, by vehicle, trip length, departure step, and storm stage, with three arrival-step rules | `Done`. `marie-curie/us-091/` and the story's details list |
| P3 | [[US-092-test-how-the-vehicle-limits-change-the\|US-092]] | Sensitivity of the limits, with closed length, share of routable pairs, detour, a regret table, and the precaution fraction | `Done`. `marie-curie/real_run_replay2_final_seed1.json` |
| P4 | [[US-093-measure-how-often-the-sticky-rule-gives\|US-093]] | Conservatism of the sticky rule against an arrival-only reference on the real graph | `Done`. `marie-curie/option_a_real_replay2_final_seed1.json` |
| P5 | None | Open the Vu 2024 report, or label the motorbike limit an assumption | Replaced by the source search of 2026-10-08 (`marie-curie/vehicle-limit-sources.md`) |
| P6 | None | Confirm the wording "sticky from the departure" | Confirmed by the user on 2026-10-02 (`US-090`, `sticky-routing-reference`) |

Copy the result files out of `marie-curie/` before use (rule 5).
Each result holds for one storm and 30 pairs (60 for `US-091`), with free-flow arrival times and 3Di depths on the model grid.
The stories state these limits.
Other work for Paper A: [[US-096-check-each-road-at-the-requested-departure|US-096]] (the engine checks each road at the requested departure) and [[BL-026-sticky-closure-clock-anchored-at-floored-departure|BL-026]] (`resolved`) explain a boundary case that the proof's Part 6 mentions.

## Paper B: end-to-end system

### Story the paper tells

1. The problem: Hanoi streets flood within minutes of a burst, and a static map is "too late". Evidence table E1 to E12 in `artifacts/docs/concepts/flood-map-reaction-time-findings.md`, which also states its limits. Related blocker: `artifacts/docs/blockers/BL-010-map-shows-forecast-not-now.md` (`resolved`).
2. The pipeline, stage by stage, with the design decisions that shaped it (see the table below).
3. Operating it: concurrency, storage, retention, and failure handling, told through resolved blockers and lessons.
4. Measured behavior: cycle time, the critical path, stage timings, storage growth, and the replays.
5. A published core output that other applications read: the contract, the manifest of each run, the read-only roles, and the analysis service.
6. Limits and what the twin does not do.

### Design decisions with a recorded reason

| Decision | Source |
| --- | --- |
| Write `flood_road_values` in place (D-001), depth per road piece is the maximum, stored in `depth` (D-006, replacing D-002 and D-005). Later replaced in stages by the edge depth table (D-038). | `artifacts/docs/decisions/decision-log.md` |
| Remove the `flood-results-full` bucket (D-004). Two test events publish under one run name (D-007). | decision log |
| `background_cycle` not run, stories dropped (D-009) | decision log |
| Build Sprint 11 before the next server run and deploy once (D-011). A replay runs 12 hours (D-012). | decision log |
| Rain forecast from Tomorrow.io (D-013) and a 15-minute cycle (D-014) | decision log |
| Archive `results_3di.nc` to the D: drive, only with real rain (D-016). Prune `flood_road_values` after 24 hours (D-017). Retire the `netcdf_values` ingest (D-018) and drop its tables (D-022). | decision log |
| Detour at half the vehicle limit and keep the hard-limit route as a second option (D-021). Keep sticky closure (D-023). | decision log |
| Run the flood tile build as its own DAG, started by an asset (D-027). The input stays `files`. | decision log, `dags/flood_tiles_dag.py` |
| Keep the latest forecast of each road piece and moment in TimescaleDB (D-028), for one year, with a moment table for dry and unknown (D-032). A run with no wet piece is dry at 0 cm (D-036). Rows keyed by piece are deleted when the key becomes `edge_key` (D-042). | decision log, [[timescaledb-schema]] |
| Show a pinned demo flood when no rain is forecast, with modes `LIVE`, `PENDING`, `DEMO` (D-030). In `DEMO` the route skips the time-aware engine (D-043). | decision log, [[graphhopper-backend]] |
| Keep the edge depth files for the newest 8 runs (D-033). Keep `TIME_AWARE_ROUTING` on (D-034). Keep the rain gate at 5 mm/h and the 50 GB archive floor (D-037). | decision log |
| One sampler and one table hold the flood depth, keyed by a stable `edge_key`, and `flood_on_roads`, `road_segment`, and `flood_road_values` are deleted in stages (D-038). | decision log, [[edge-depth-table-format]] |
| Keep the storm replay of 2026-10-10 as a permanent test dataset, rebuilt from the NetCDF when a test needs it (D-039) | decision log, [[test-dataset]] |
| Raster tiles replaced by vector polygon tiles | `artifacts/archive/plans/flood-extent-polygon-tiles-airflow-minio.md`, `artifacts/docs/concepts/raster-first-flood-pipeline.md` |
| Valhalla replaced by GraphHopper (ADR-002) | `artifacts/raw/T3-Digital-Twin_Architecture.md` working copy, section on ADRs |
| Routing tasks moved to their own DAG `routing_adapter`, triggered by an Airflow asset event, so a routing failure leaves the core run green | [[US-073-move-the-routing-owned-tasks-into-their\|US-073]], `dags/routing_adapter_dag.py` |
| Rain-gated simulation with hot start from gauge levels | `artifacts/docs/concepts/3di-simulation-orchestration.md`, `scripts/hotstart_policy.py`, `test/test_flood_rain_gate.py` |

### Performance and operations evidence

| Topic | Source |
| --- | --- |
| Why native 1 m sampling was slow (a Python per-pixel loop, a cost model of 3.68 s plus 5.26e-5 s per valid cell) | Project memory file `sample_rate_1_bottleneck.md` (2026-09-08). It describes the retired GeoJSON chain, so cite it only as history that motivated the raster-first design, never as a current limit. |
| Narrowing the per-run critical path, stage margins | `artifacts/archive/plans/us-037-narrow-the-per-run-critical-path.md`, `scripts/pipeline_margins/`, `marie-curie/us-037/` (experiment CSVs and `experiment-results.txt`) |
| Soak and the 12-hour storm event construction | `artifacts/archive/plans/us-063-realistic-rain-replay-for-us-037-and-us-034.md`, `artifacts/docs/concepts/rain-replay-test-environment.md`, `artifacts/archive/plans/september-2026-storm-rain-replay.md`, `scripts/rain_replay.py`, `scripts/rain_events/`, `scripts/rain_env/`, `marie-curie/us-088/` |
| Worker concurrency serialized the runs | `artifacts/docs/blockers/BL-013-flood-mapping-full-worker-concurrency-serializes-runs.md` |
| Slow sampling step (9c over 770 s) and its cancel rule | `artifacts/docs/blockers/BL-023-9c-sampling-step-runs-over-770-seconds.md`, [[US-070-stop-a-slow-sampling-step-from-holding\|US-070]] |
| The rain gate stopped simulating while the flood still stood, and the fix | `artifacts/docs/blockers/BL-028-rain-gate-stops-simulation-while-the-flood-still-stands.md`, `US-101`, `US-102` |
| Disk filled by Docker's VHDX twice | `artifacts/docs/blockers/BL-022-docker-data-vhdx-fills-c-drive-again.md`, `artifacts/logs/2026-10-04-docker-vhdx-disk-full.md`, `artifacts/logs/2026-10-02-disk-cleanup-and-d-drive-move.md`, `artifacts/archive/plans/move-non-ssd-storage-to-d-drive.md` |
| Hot-start state saved at the end of a run | `artifacts/archive/blockers/BL-009-hotstart-state-saved-at-end-of-run.md` |
| Edge ids drift on graph re-import, and the stable `edge_key` that fixes it | `artifacts/docs/concepts/graph-reimport-procedure.md`, `US-117` |
| Overlay and metrics change grain from road pieces to graph edges (the overlay area is about 2.2 times the old one for the same run) | [[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table\|US-119]] details item 6, [[US-121-read-the-flood-metrics-from-the-edge-table\|US-121]] |
| Two flood tile inputs measured on 5 paired runs | `artifacts/docs/stories/US-104-compare-the-two-inputs-of-the-flood-tile-build.md`, [[decision-log\|D-027]] |
| Depth history size, compression, and the moment table | [[US-105-decide-what-flood-history-the-industry-apps-need\|US-105]], [[timescaledb-schema]], `US-106`, `US-127` |
| Replacing `flood_road_values` with the edge depth table: measurements and the staged plan | [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values\|US-115]], [[decision-log\|D-038]] |
| A kept real storm as a test dataset, snapshot, restore, and rebuild | [[test-dataset]], [[US-124-save-the-storm-replay-results-and-derived-data\|US-124]], [[US-125-restore-the-snapshot-into-test-databases\|US-125]] |
| Run manifest, read-only roles, and the analysis service | [[US-107-create-a-read-only-role-for-any-consumer-app\|US-107]], [[US-108-publish-a-run-manifest-for-the-core-outputs\|US-108]], [[US-109-run-an-analysis-service-in-its-own-container\|US-109]], [[analysis-service]] |
| Point depth lookup speed, connection pooling, forecast verification | `artifacts/archive/epics/EP-03-point-depth-lookup-backend.md`, `artifacts/docs/blockers/BL-007-flood-points-connection-per-request.md`, `artifacts/docs/stories/evidence/connection-pooling-and-forecast-verification.png` |
| Frontend (vendored GraphHopper Maps fork), mockup recheck | `artifacts/raw/frontend-mockups/`, [[EP-19-frontend-against-the-mockup\|EP-19]], the archived epics `EP-01-frontend-depth-features.md`, `EP-02-frontend-polish.md`, `EP-05-mockup-screen-coverage.md`, `EP-11-frontend-mockup-recheck.md` in `artifacts/archive/epics/`, `floodmap/graphhopper-maps/` |
| NetCDF values storage redesign, then its retirement | `artifacts/docs/stories/US-066-netcdf-values-storage-redesign.md`, `artifacts/archive/plans/netcdf-values-timescale-migration.md`, `US-095`, [[decision-log\|D-018]] |
| Screenshots of working stories | `artifacts/docs/stories/evidence/` (102 images, plus the check scripts and their captured output) |

### Process material (optional, for a short "engineering lessons" section)

- Twelve lessons in `artifacts/docs/lessons/lessons.md` (`L-001` to `L-012`), each distilled from a resolved blocker or a verification slip.
- The blocker pages `BL-001` to `BL-029`. The current ones are in `artifacts/docs/blockers/` (status in each frontmatter) and the finished ones are in `artifacts/archive/blockers/`.
- Daily logs `artifacts/archive/logs/2026-09-13.md` to `2026-09-30.md` and `artifacts/logs/2026-10-01.md` to `2026-10-12.md` give the order of events. Each log opens with a summary of the previous day.
- The project adopted Scrum on 2026-10-10 ([[decision-log|D-024]], [[scrum-framework]]). The four sprint plans `SP-01` to `SP-04` are in `artifacts/archive/sprints/`, and the current sprint files are `artifacts/docs/sprints/SPR-013-*.md` and `SPR-014-*.md`. The epics are `EP-17` to `EP-22` in `artifacts/docs/epics/`, and `EP-01` to `EP-16` are archived. The stories are `US-001` to `US-131` in `artifacts/docs/stories/`.

### Author decisions, confirmed 2026-10-08

- The author has already written a separate paper on the flood model, including its validation. Paper B does not validate the hydrodynamic model. It cites that paper for the model and its validation, and it is a systems paper. Ask the author for the citation and the arXiv or venue status of the flood model paper before drafting the related-work text.
- Paper B may report operator-side facts: the server host, the Windows Docker host, and the cost of 3Di compute. The vault records them in `.claude/CLAUDE.md` and the logs.
- The writing job starts only after the 12-hour replay and the routing experiments P2 to P4 have produced numbers. Both are now `Done`, so the author decides the start date.
- The working titles in "The two papers" are approved.

## How to run the writing job

1. Re-read this page, `artifacts/TODOS.md`, and the logs dated after 2026-10-13. Update the results table and the list of built-and-unchecked stories.
2. Ask the author to confirm the two titles and the one-claim statements above.
3. For each paper, run `research-writing-assistant:paper-orchestration`: outline with an evidence map first (`/ars-outline` is available), then one section at a time, each checked against its cited file.
4. Run `research-writing-assistant:peer-review` and `/ars-citation-check` before calling a draft ready. Verify every citation was opened (see `failed-sources.md`).
5. Output LaTeX in an arXiv-compatible layout. Use `research-writing-assistant:latex-output`.
6. Report to the author which placeholders remain and which experiments or server checks they wait on.
