---
date: 2026-10-08
type: reference
status: draft
tags: [paper, arxiv, handoff, routing, system]
related: ["[[T3-Digital-Twin_Architecture]]", "[[sticky-c-lite-routing]]", "[[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]", "[[sticky-routing-reference]]", "[[3di-simulation-orchestration]]", "[[core-output-contract]]", "[[decision-log]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[SP-04-frontend-recheck|sprint-plan-4]]", "[[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]]", "[[flood-map-reaction-time-findings]]"]
---

# Handoff for two arXiv papers: flood routing and the end-to-end system

This page is the brief for the agent that writes two papers about the t3-digital-twin project. It maps every claim to the file that backs it and says which results exist, which are pending, and which the agent must never state as fact.

Written 2026-10-08 on branch `modular`. Everything here is a pointer. The agent reads the cited files and checks each number against its source before using it.

## The two papers

| | Paper A, routing | Paper B, end-to-end system |
| --- | --- | --- |
| Working title | Time-aware flood routing with sticky closure on forecast depth | A 15-minute flood digital twin for Hanoi: from rain forecast to vehicle-aware routes |
| One claim to remember | A route planned on forecast depth stays safe on arrival. Sticky closure keeps the search a plain forward Dijkstra, so it is exact and costs the same order as a static search. | A 3Di-based digital twin can publish flood depth, map tiles, and a routing input every 15 minutes, on one server, from an operational rain forecast. |
| Kind | Algorithm and measurement | Systems and engineering experience |
| Suggested arXiv primary | cs.DS, cross-list cs.CY and cs.AI | cs.DC, cross-list cs.DB |
| Why those | The proof and complexity argument are computing-core. | Pipeline, storage, and scheduling are computing-core. |

The author is applying to a computing master's program. Keep both papers in computing categories. Do not put either in physics.geo-ph or a hydrology category. The hydrology is the setting, not the contribution.

A first-time arXiv submitter needs an endorsement in the chosen category. Raise this with the author before the writing is done.

## Rules for the agent

1. Paper text is research writing. Invoke the research-writing skills from the user's global instructions first: `research-writing-assistant:using-research-writing`, then `paper-orchestration`, `evidence-driven-writing` with `literature-review` for the Introduction and Related Work, `experiment-results-planning` for Results, `writing-chapters` with `writing-core`, and `peer-review` before calling a section ready. Do not use `pstack:technical-writing`, `pstack:unslop`, or `pstack:poteto-mode` on paper text.
2. Write nothing from memory. Open the cited file and quote its number. The vault says which facts are verified and which are marked unverified. Keep that distinction.
3. Mark any missing result as a placeholder, for example `[RESULT: violation rate, Question 1]`. Never invent a number.
4. Do not edit anything under `artifacts/raw/`. It is read-only.
5. `marie-curie/` is untracked scratch space and can be deleted at any time. Copy what a paper needs (tables, bibliography) into a new folder, for example `papers/`, before relying on it. Ask the author before creating that folder.
6. Name the providers: 3Di, GraphHopper, Tomorrow.io (the live rain forecast, D-013 in the decision log), and NASA IMERG (the offline storm replay). Do not name NCHMF as a data source. The original design used it, and NCHMF did not approve API access. The 15-minute cycle is approved (D-014).

## Claims the papers must not make

These come from the vault's own caveats.

- Name the storm behind every result. The 12-hour replay is the real 2026-09-16 Hanoi event (NASA IMERG rain, `marie-curie/us-088/hanoi_20260916_storm.csv`), so it is not synthetic. The earlier constant 50 mm/h storm is synthetic. The reviewer-questions note (`marie-curie/idea-routing-paper-reviewer-questions.md`, Question 1 threats) was written on 2026-10-02 before the replay existed, so its "synthetic" wording applies only to the 50 mm/h storm.
- Even on the real event, depths are 3Di model output, not observed depths. A violation rate is a rate in the model driven by real rain. Do not present it as a measured rate of drivers meeting closed roads.
- The vehicle depth limits (motorbike 20 cm, car 30, truck 35, foot 40; `VEHICLE_PROFILES` in `scripts/.../flood_utils.py`, confirm the path) are policy parameters. A source search on 2026-10-08 (`marie-curie/vehicle-limit-sources.md`, copy it first) found this support. Never call a threshold safe.
  - Car 30 cm is supported for a small passenger car by Shand et al. 2011 and the Australian AIDR guidance (both 0.3 m). UK guidance gives 0.5 m for most cars and vans.
  - Motorbike 20 cm is partly supported. The best source is Ho Chi Minh City police guidance reported by Thanh Niên on 2026-10-06 (care below about 15 cm, do not push on at 20 to 30 cm). No peer-reviewed motorbike stall experiment exists. Do not cite the Vu 2024 report for the limit, because it could not be opened.
  - Truck 35 cm has no source. Shand lists commercial vehicles as a data gap. Call it an assumption.
  - Foot 40 cm is partly supported. It sits below the Cox 2010 depth caps (0.5 m for children, 1.2 m for adults), which the search read only through a secondary report. No source gives 40 cm, and the literature ties depth to velocity.
  - Experiment P5 is replaced by this search. P3 (sensitivity) is now the main defense of the limits.
- Sticky closure is conservative. A road that drained stays closed for a traveller who arrives after it drained. It is exact for the sticky rule, not for the true arrival-time rule. Source: reviewer-questions note, Question 3.
- The proof of the FIFO argument is a sketch in the reviewer-questions note, not a finished proof. Paper A needs a written lemma and proof (see work item P1).
- The 15-minute refresh is not the weakest link for short convective bursts. The rain forecast is. That is an inference in `artifacts/docs/concepts/flood-map-reaction-time-findings.md`, not a measurement. No source gives a measured rate of rise in cm per minute for Hanoi.
- The IMERG area average over the model extent totals 84.95 mm with a peak of 8.73 mm/h, against about 200 mm at the heaviest stations. The replay is gentler than the news reports. Source: `artifacts/logs/2026-10-08.md`, section "US-088".
- `background_cycle` and the 24-bar histogram were dropped (D-009). Do not describe them as part of the built system.

## Server state on 2026-10-08

Verified read-only on the server.

- The time-aware engine is deployed and was tested on the server on 2026-10-07, and the flag is off at rest. `floodmap-backend` has `TIME_AWARE_ROUTING=false`, so ordinary live routing still judges every road at one timestep. The rollout script (`scripts/routing_proof/rollout.ps1`) turns the flag on for the proof, routes the fixed pairs in both modes, and puts it back off unless run with `-LeaveOn` (`artifacts/docs/claude-plan/engine-server-proof-and-rollout.md`, steps 5 to 10). Whether `-LeaveOn` was used on 2026-10-07 is unconfirmed, but the flag read false afterward.
- The recorded server proof (`artifacts/TODOS.md`, US-055 status note, 2026-10-07): `compare` changed 37.5% of routes with a median detour of 0.94, `crossings` 0, `departures` 3 of 3 trips, `latency` all 6 cells within 2 times the US-046 baseline, `scenario-check.sh` 32 of 32. Read the raw outputs from the evidence screenshots and logs before quoting these numbers. Still open: US-045 (live DAG timing), run with the 12-hour replay.
- Paper A may report these as server-proof results. It must not say time-aware routing serves users in production while the flag is off.
- `flood_mapping_full` and `routing_adapter` are unpaused. The cycle is 15 minutes (D-014). The rain forecast is Tomorrow.io (D-013). The replay reads `hanoi_20260916_storm.csv` with start `2026-10-08T08:45:00Z`, gate 5 mm/h, lookahead 2 hours, simulation duration 7200 s, worker concurrency 4.
- Retention: `FLOOD_EXTENT_KEEP_RUNS=8`, `EDGE_TABLE_KEEP_RUNS=3`, `FLOOD_EXTENT_TILE_STEPS=2`.
- The worker still carries variables of the retired GeoJSON chain (`SAMPLE_RATE=20`, `UPDATE_INTERVAL`, `KEEP_LOCAL_GEOJSON`, `VALHALLA_PORT`). The `sample_rate_1_bottleneck` memory note describes that retired chain. Do not cite it as a limit of the current pipeline. Cite the current critical path from `artifacts/archive/plans/us-037-narrow-the-per-run-critical-path.md` instead.

## Results status on 2026-10-08

| Result | Used by | Status | Where it will land |
| --- | --- | --- | --- |
| 12-hour rain replay (event `hanoi_20260916_storm.csv`, gate 5 mm/h, 42 runs in 2 chains, last run 2026-10-09 03:00 +07) | B | Running on the server | `artifacts/TODOS.md` US-045 update, then a log |
| Edge depth table build time, file size, edge count (US-045); unloaded numbers so far 42.0 s and 1,085,48x edges (read the exact figure from TODOS.md) | B | Needs live runs of task `9c` | `artifacts/docs/concepts/edge-depth-table-format.md`, `artifacts/docs/prds/PRD-003-edge-depth-table.md` |
| Routing latency: p50 and p95 of `POST /route` within 2 times the US-046 baseline | A, B | In progress (US-055) | `artifacts/TODOS.md` US-055, `scripts/routing_proof/` |
| Four scenarios times four vehicles pass the checker on the deployed image | A | In progress (US-055) | `scripts/routing_proof/routing_proof.py`, `scripts/routing_reference/scenarios.py` |
| Question 1, violation rate of single-timestep routing | A | Planned, nothing run as of 2026-10-02. Confirm in the logs. | To be created from `scripts/routing_reference/` |
| Question 2, sensitivity of the limits and a regret table | A | Planned, same note | Same |
| Question 3, proof and conservatism measurement | A | Planned, same note | Same |
| 9c sampling-step time under load (US-070; run `20261006T104500` took 51.1 s) | B | Resolved 2026-10-10 | `artifacts/docs/blockers/BL-023-9c-sampling-step-runs-over-770-seconds.md` |
| Storage growth over the replay (US-069) | B | Open. D-012 shortens the window to 12 hours, so the 24-to-48-hour reading is not possible. | `artifacts/TODOS.md` US-069 |

The author chose to hold the writing until the 12-hour replay and the routing experiments have produced numbers. Re-read this table, `artifacts/TODOS.md`, and the newest logs at the start of the writing job, then update the table.

## Shared background: what the system is

Read in this order.

1. `artifacts/raw/T3-Digital-Twin_Architecture.md` and its working copy `artifacts/docs/concepts/architecture-block-diagram.md`. The raw file is the original design and predates two decisions (vector tiles replaced raster tiles, GraphHopper replaced Valhalla). The concept page marks each component Built or Designed, not built. Describe only what is Built.
2. `artifacts/docs/concepts/3di-simulation-orchestration.md`. The Airflow DAG `dags/flood_mapping_dag.py` (`flood_mapping_full`) runs one cycle every 15 minutes: check the rain forecast, decide whether to simulate, run 3Di, download `results_3di.nc`, compute depth rasters, then fan out to the tile task, the depth raster load, and the flood-on-roads task.
3. `artifacts/docs/concepts/core-output-contract.md`. The five PostgreSQL tables, the edge depth files, and the vector tiles that the pipeline publishes. Routing is the first consumer. Verified against code at commit `5e4a314`.
4. `artifacts/docs/concepts/minio-flood-extent-pipeline.md`. Depth raster to polygon tiles in MinIO plus a PostGIS audit copy.
5. `artifacts/docs/concepts/flood-on-roads.md`, `road-segment-table.md`, `flood-metric-extractor.md`, `timescaledb-schema.md`. Depth per road piece and the metrics derived from it.
6. `artifacts/docs/concepts/graphhopper-backend.md`. The backend in `floodmap/graphhopper-flood-road/backend/server.py`, between the frontend and a pinned GraphHopper.

Hanoi model border for any coordinate used in a figure or test: longitude 105.7015 to 105.7971, latitude 20.9754 to 21.0269 (`.claude/CLAUDE.md`, "Test points stay inside the model border").

## Paper A: routing

### Story the paper tells

1. Today's backend builds one GraphHopper `custom_model` from a single forecast timestep, so every road on a route is judged at one moment. A road that is dry now and floods in 10 minutes passes. Source: `artifacts/docs/blockers/BL-011-routing-not-time-aware.md` (status open), scenario table.
2. The design: sticky C-lite. Each edge closes at its first flooded step at or after departure and stays closed to the end of the horizon. Source: `artifacts/raw/ideas/sticky-c-lite-routing/sticky-c-lite-routing.md`, "Idea" and "Why we choose it".
3. Why it is exact and cheap: with closures that only grow, the arrival function is non-decreasing (FIFO), so waiting never helps and a forward time-dependent Dijkstra is exact. Sketch in `marie-curie/idea-routing-paper-reviewer-questions.md`, Question 3.
4. Why it does not contradict the hardness result: Kleff et al. (SEA 2020) show NP-hardness when waiting is allowed only at dedicated places and closures reopen. Sticky closure forbids reopening inside a query.
5. Evidence: the offline reference and checker, the Java engine compared against the reference, the server proof, and the three reviewer questions.

### Design and implementation sources

| Topic | File |
| --- | --- |
| Requirements | `artifacts/docs/prds/PRD-004-time-aware-routing-engine.md` (draft, has Decisions and open questions) |
| Edge depth table requirements and format | `artifacts/docs/prds/PRD-003-edge-depth-table.md`, `artifacts/docs/concepts/edge-depth-table-format.md`, `scripts/edge_depth/edge_depth_table.py` |
| Reference implementation and checker | `artifacts/docs/concepts/sticky-routing-reference.md`, `scripts/routing_reference/` (`sticky_reference.py`, `corridor.py`, `scenarios.py`, `run_scenarios.py`) |
| Depth to cost model, `DEPTH_BANDS` | `artifacts/docs/concepts/routing-depth-threshold-model.md`, `floodmap/graphhopper-flood-road/backend/flood_areas.py` |
| Graph edge ids change on re-import | `artifacts/docs/concepts/graph-reimport-procedure.md` |
| Departure advice ("wait until") | `artifacts/docs/claude-plan/departure-time-advice-research.md`, `route-departures-endpoint.md`, `wait-until-alert.md` |
| Plans and stories | `artifacts/archive/plans/time-aware-weighting-and-search.md`, `time-aware-routing-prds-and-sprint-plan.md`, `engine-server-proof-and-rollout.md`, `artifacts/docs/epics/EP-09-time-aware-routing-engine.md`, `EP-08-edge-depth-table.md`, `EP-10-routing-first-consumer.md` |
| Server proof tooling | `scripts/routing_proof/` (`routing_proof.py`, `pairs.json`, `rollout.ps1`), `scripts/backend_soak/` |
| Java engine | `java/` (read its build notes in `artifacts/archive/plans/sprint-6-java-toolchain-and-edge-export.md`) |
| Engine tests | `scripts/routing_reference/test_*.py`, `floodmap/graphhopper-flood-road/backend/test_core_contract.py` |

### Literature

All in `marie-curie/lit-review-flood-routing/`. Copy it before use (rule 5).

- `sources.md` is an annotated bibliography with 69 entries, S01 onward. S01 is Kleff et al. 2020, S02 Zeitz 2022, S03 Kaufman and Smith 1993, S05 Orda and Rom 1990, S06 Dean 2004, S17 and S18 Pregnolato 2017 (depth-disruption function), S43 Shand et al. (vehicle stability), S35 Kasmalkar (sensitivity), S48 Manila paper on the Ho Chi Minh City motorbike figure.
- `search-log.md` records 93 searches run on 2026-10-02, with what was found and what was blocked.
- `failed-sources.md` lists sources that could not be opened. Do not cite any of them as read.
- `pdf/` holds the full texts that were opened.
- The finding to build on: time-dependent routing with closures and waiting is established, and flood-aware routing is established. The defensible contribution is the careful combination, the sticky-closure argument, and the measured safety gap. The reviewer-questions note says this directly.

### Experiments to run or finish (work items for the author, not the agent)

| ID | Story and sprint | Experiment | Source of the plan |
| --- | --- | --- | --- |
| P1 | `US-090`, Sprint 12 | Write the FIFO lemma and the correctness proof of the forward search; check step-boundary cases; confirm the landmark heuristic stays admissible (story R4 plans a unit test) | Reviewer-questions note, Question 3 |
| P2 | `US-091`, Sprint 12, Done | Violation rate of single-timestep routes on arrival, by vehicle, trip length, departure step, and storm stage; report three arrival-step rules | Question 1 |
| P3 | `US-092`, Sprint 12 | Sensitivity of the limits (motorbike 10 to 40 cm, truck 25 to 60 cm, band start 25, 50, 75 percent) with closed length, share of pairs still routable, mean detour, and a regret table | Question 2 |
| P4 | `US-093`, Sprint 12 | Conservatism of the sticky rule against an arrival-only reference | Question 3, item 4 |
| P5 | Done, no story | Open the Vu 2024 report and the Manila paper's citation of it, or label the motorbike limit an assumption. Replaced by the source search of 2026-10-08 (`marie-curie/vehicle-limit-sources.md`) | Question 2 |
| P6 | None | Confirm with the author the wording "sticky from the departure step" (open question in the PRD) | `time-aware-routing-engine.md` |

Order of work from the note: P2 first (needs no new engine), then P1 and P4, then P3. The stories are in [[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]], all in Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] (scheduled 2026-10-08). The frontend recheck waits for [[SP-04-frontend-recheck|sprint-plan-4]] so the routing finishes first.

## Paper B: end-to-end system

### Story the paper tells

1. The problem: Hanoi streets flood within minutes of a burst, and a static map is "too late". Evidence table E1 to E12 in `artifacts/docs/concepts/flood-map-reaction-time-findings.md`, which also states its limits. Related blocker: `artifacts/docs/blockers/BL-010-map-shows-forecast-not-now.md`.
2. The pipeline, stage by stage, with the design decisions that shaped it (see the table below).
3. Operating it: concurrency, storage, retention, and failure handling, told through resolved blockers and lessons.
4. Measured behavior: cycle time, the critical path, stage timings, storage growth, and the replay.
5. Limits and what the twin does not do.

### Design decisions with a recorded reason

| Decision | Source |
| --- | --- |
| Write `flood_road_values` in place (D-001); depth per road piece is the maximum, stored in `depth` (D-006, replacing D-002 and D-005) | `artifacts/docs/decisions/decision-log.md` |
| Remove the `flood-results-full` bucket (D-004); two test events publish under one run name (D-007) | decision log |
| `background_cycle` not run, stories dropped (D-009) | decision log |
| Build Sprint 11 before the next server run and deploy once (D-011); a replay runs 12 hours (D-012) | decision log |
| Raster tiles replaced by vector polygon tiles | `artifacts/archive/plans/flood-extent-polygon-tiles-airflow-minio.md`, `raster-first-flood-pipeline.md` |
| Valhalla replaced by GraphHopper (ADR-002) | `artifacts/raw/T3-Digital-Twin_Architecture.md` working copy, section on ADRs |
| Routing tasks moved to their own DAG `routing_adapter`, triggered by an Airflow asset event, so a routing failure leaves the core run green | `artifacts/TODOS.md` US-073, `dags/routing_adapter_dag.py` |
| Rain-gated simulation with hot start from gauge levels | `artifacts/docs/concepts/3di-simulation-orchestration.md`, `scripts/hotstart_policy.py`, `test/test_flood_rain_gate.py` |

### Performance and operations evidence

| Topic | Source |
| --- | --- |
| Why native 1 m sampling was slow (a Python per-pixel loop, a cost model of 3.68 s plus 5.26e-5 s per valid cell) | Project memory file `sample_rate_1_bottleneck.md` (2026-09-08). It describes the retired GeoJSON chain, so cite it only as history that motivated the raster-first design, never as a current limit. |
| Narrowing the per-run critical path, stage margins | `artifacts/archive/plans/us-037-narrow-the-per-run-critical-path.md`, `scripts/pipeline_margins/`, `marie-curie/us-037/` (experiment CSVs and `experiment-results.txt`) |
| Soak and the 12-hour storm event construction | `artifacts/docs/claude-plan/us-063-realistic-rain-replay-for-us-037-and-us-034.md`, `rain-replay-test-environment.md`, `september-2026-storm-rain-replay.md`, `scripts/rain_replay.py`, `scripts/rain_events/`, `scripts/rain_env/`, `marie-curie/us-088/` |
| Worker concurrency serialized the runs | `artifacts/docs/blockers/BL-013-flood-mapping-full-worker-concurrency-serializes-runs.md` |
| Slow sampling step (9c over 770 s) and its cancel rule | `artifacts/docs/blockers/BL-023-9c-sampling-step-runs-over-770-seconds.md` |
| Disk filled by Docker's VHDX twice | `artifacts/docs/blockers/BL-022-docker-data-vhdx-fills-c-drive-again.md`, `artifacts/logs/2026-10-04-docker-vhdx-disk-full.md`, `2026-10-02-disk-cleanup-and-d-drive-move.md`, `artifacts/archive/plans/move-non-ssd-storage-to-d-drive.md` |
| Hot-start state saved at the end of a run | `artifacts/archive/blockers/BL-009-hotstart-state-saved-at-end-of-run.md` |
| Edge ids drift on graph re-import | `artifacts/docs/concepts/graph-reimport-procedure.md` |
| Point depth lookup speed, connection pooling, forecast verification | `artifacts/docs/epics/EP-03-point-depth-lookup-backend.md`, `artifacts/docs/blockers/BL-007-flood-points-connection-per-request.md`, `artifacts/docs/stories/evidence/connection-pooling-and-forecast-verification.png` |
| Frontend (vendored GraphHopper Maps fork), mockup recheck | `artifacts/raw/frontend-mockups/`, `artifacts/docs/epics/EP-01-frontend-depth-features.md`, `EP-02-frontend-polish.md`, `EP-05-mockup-screen-coverage.md`, `EP-11-frontend-mockup-recheck.md`, `floodmap/graphhopper-maps/` |
| NetCDF values storage redesign | `artifacts/docs/stories/US-066-netcdf-values-storage-redesign.md`, `artifacts/archive/plans/netcdf-values-timescale-migration.md` |
| Screenshots of working stories | `artifacts/docs/stories/evidence/` (86 files) |

### Process material (optional, for a short "engineering lessons" section)

- Eleven lessons in `artifacts/docs/lessons/`, each distilled from a resolved blocker.
- The 23 blocker pages in `artifacts/docs/blockers/` (status in each frontmatter).
- Daily logs `artifacts/archive/archive/logs/2026-09-13.md` to `2026-10-08.md` give the order of events. Each log opens with a summary of the previous day.
- Sprint plans `artifacts/docs/sprints/SP-01-prd-and-backlog.md` to `SP-04-frontend-recheck.md`, the epics under `artifacts/docs/epics/`, and the stories under `artifacts/docs/stories/` (US-001 to US-093).

### Author decisions, confirmed 2026-10-08

- The author has already written a separate paper on the flood model, including its validation. Paper B does not validate the hydrodynamic model. It cites that paper for the model and its validation, and it is a systems paper. Ask the author for the citation and the arXiv or venue status of the flood model paper before drafting the related-work text.
- Paper B may report operator-side facts: the server host, the Windows Docker host, and the cost of 3Di compute. The vault records them in `.claude/CLAUDE.md` and the logs.
- The writing job starts only after the 12-hour replay and the routing experiments P2 to P4 have produced numbers.
- The working titles in "The two papers" are approved.

## How to run the writing job

1. Re-read this page, `artifacts/TODOS.md`, and the logs dated after 2026-10-08. Update the results table.
2. Ask the author to confirm the two titles and the one-claim statements above.
3. For each paper, run `research-writing-assistant:paper-orchestration`: outline with an evidence map first (`/ars-outline` is available), then one section at a time, each checked against its cited file.
4. Run `research-writing-assistant:peer-review` and `/ars-citation-check` before calling a draft ready. Verify every citation was opened (see `failed-sources.md`).
5. Output LaTeX in an arXiv-compatible layout. Use `research-writing-assistant:latex-output`.
6. Report to the author which placeholders remain and which experiments they wait on.
