---
date: 2026-10-07
type: plan
branch: modular
status: active
tags: [plan, sprint-11, server, rollout, us-055, us-072, us-073, us-045, us-069]
related: ["[[engine-server-proof-and-rollout]]", "[[routing-first-consumer-contract]]", "[[core-output-contract]]", "[[3di-simulation-orchestration]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[edge-depth-table-server-proof]]", "[[BL-023-9c-sampling-step-runs-over-770-seconds|9c-sampling-step-runs-over-770-seconds]]"]
---

# Plan: one server deploy for Sprint 9 to 11

## Context

On 2026-10-07 the user asked to build everything before any further 48-hour run, because a run costs a lot. Branch `modular` holds all of it: the engine stories (`US-051` to `US-054`), the contract and its guards (`US-071`, `US-074`, `US-075`), the read-only role (`US-072`), and the `routing_adapter` DAG (`US-073`). Nothing is pushed or deployed. The server is still in the replay window, which ends at 00:00 +07 on 2026-10-08, and no image builds on it until then.

This plan orders the server work so one deploy and one short DAG run close the most stories. The order is derived from the code and the agents' reports. It has not been run.

## Ordering facts that constrain the steps

1. `compose.yml` now gives `floodmap-backend` the login `routing_reader` and refuses to interpolate without `ROUTING_READER_PASSWORD`. Every `docker compose` command fails until `.env` has that line.
2. The backend cannot connect until the role exists. `rollout.ps1` recreates the backend, so the role must exist before `rollout.ps1` runs.
3. The role script reads the contract page and needs only the existing backend image, the repo mounted read-only, and the writer login from `.env`.
4. `routing_adapter` starts unpaused and runs only on an asset event from `9b_load_depth_raster`. While `flood_mapping_full` is paused, it never runs. The task `9c` and the `US-073` timing need a few real core runs.
5. The three routing tasks stay unscheduled until the Airflow pool `routing_adapter` exists.
6. `US-055` assumed today's DAG shape for its timing tool. `rollout.ps1` only checks that the core DAG is paused, and `table_timing.ps1` was rewritten for the new DAG, so one deploy is consistent. If `US-055` is to run on the old shape alone, deploy the `US-055` commits first and the rest later. That costs a second deploy.

## Steps, in PowerShell on the server in `C:\Users\TECOTEC\airflow_new`

Use `;` and never `&&`. Run compose commands on the host, not through the Mac context.

1. Wait for the replay to end. Read the 48-hour storage numbers for `US-069` and the timing for `US-045` first (`scripts/storage_check/read_storage.ps1`, `scripts/edge_depth/table_timing.ps1`).
2. Push `modular` from the Mac to `origin` (`alice182012-dev/t3-digital-twin`), then `git fetch origin; git checkout modular; git pull origin modular` on the server. The push is yours to make.
3. Add the reader password: `Add-Content .env "ROUTING_READER_PASSWORD=<new secret>"`.
4. Create the role (`US-072`): `docker run --rm --network airflow_new_default --env-file .env -e POSTGRES_HOST=storage-postgres -v "${PWD}:/repo:ro" -w /repo airflow_new-floodmap-backend python scripts/database/create_routing_reader_role.py`. Expect `Role routing_reader can read flood_depth_raster_tile, flood_extent_polygon, flood_extent_step, flood_road_values, graph_edge.`
5. Create the pool: `docker compose exec airflow-apiserver airflow pools set routing_adapter 1 "Routing tasks of routing_adapter, one at a time"`.
6. Run `scripts/routing_proof/rollout.ps1` (`US-055`, [[engine-server-proof-and-rollout]]). It builds the three images and recreates the services, so the backend comes up as `routing_reader`.
7. Run the reader checks (`US-072`): `docker compose exec floodmap-backend python backend/test_reader_role.py`, expect `ok: routing_reader reads 5 contract tables and writes nothing`. Then `python backend/test_core_contract.py` (expect `live schema matches the contract for 5 tables`) and call `/flood/runs`, `/flood/timesteps`, `/flood/areas`, `/flood/points`, and `/flood/forecast`. Then run the soak known-answer check for `POST /route`: `docker --context remote-server exec -i airflow_new-floodmap-backend-1 python - roads --per-bucket 6 < scripts/backend_soak/soak_checks.py`. Check the backend log has no `permission denied`.
8. Check the DAGs import: `docker compose exec airflow-worker airflow dags list-import-errors`, then `airflow dags list` and find `routing_adapter`.
9. Unpause `flood_mapping_full` for about one hour (four slots). This is the only DAG run needed for `US-045`, `US-070`, and `US-073`.
10. Read the asset events: `docker --context remote-server exec airflow_new-airflow-postgres-1 psql -U airflow -d airflow -c "select source_run_id, extra from asset_event order by id desc limit 5"`. `extra` must hold `run_ts`.
11. Measure `9c`: `.\scripts\edge_depth\table_timing.ps1 -Runs 20`. The limit is 5 minutes after `3_calculate_depth`. The report also covers `US-045`.
12. Trigger `routing_adapter` once by hand and read the log for `from the newest published event` (the manual fallback).
13. Pause `flood_mapping_full` again unless the next phase needs it running.
14. Take the evidence screenshots (`US-071` to `US-075`, `US-051` to `US-055`, `US-045`), then move the stories to `Done`.

## Rollback

- `US-072`: set the two backend lines in `compose.yml` back to `POSTGRES_USER` and `POSTGRES_PASSWORD`, then run `docker compose up -d --no-deps floodmap-backend`. The role can stay.
- `US-073`: check out the commit before `77169c3`. The pool and the asset can stay.

## Risks

- `rollout.ps1` has never run. Its first run is its test ([[engine-server-proof-and-rollout]]).
- Step 7 has no earlier proof. The role script, the live reader test, and every endpoint on the reader role are untested. A failure in step 6 may come from the role, not from the engine. To separate the two, run steps 4 and 7 against the old backend container before step 6.
- The asset event's `extra`, the shape of `triggering_asset_events`, and the `inlet_events` fallback were read from the 3.1.7 source and unit-tested with stand-ins. Step 10 is their first real check.
- Folded events: two events inside one scheduler loop produce one routing run, and the older run gets no `flood_road_values`. Rare at a 15-minute slot.
- The Java `TimeAwareRouterTest` runs in the `graphhopper` image build of step 6.

## Status history

- **2026-10-07, active.** Plan written. Nothing pushed or deployed.
