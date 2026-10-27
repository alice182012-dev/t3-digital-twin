---
date: 2026-10-12
type: concept
status: active
tags: [analysis, container, roles, compose]
related: ["[[core-output-contract]]", "[[timescaledb-schema]]", "[[EP-21-industry-analysis-on-the-flood-data|EP-21]]", "[[US-109-run-an-analysis-service-in-its-own-container|US-109]]", "[[US-107-create-a-read-only-role-for-any-consumer-app|US-107]]"]
last_updated: 2026-10-13
---

# Analysis service

The analysis service is the container for the industry analysis applications of [[EP-21-industry-analysis-on-the-flood-data|EP-21]].
It has its own image, its own requirements file, and its own schema, so an analysis developer adds libraries and tables without touching the Airflow image or the pipeline tables.
The code is in `analysis-service/`, and the service is `analysis` in `compose.yml`.

## Endpoint

`GET /health` returns `{"run_ts": "<run>"}`.
The run is the newest `run_ts` whose set of outputs in `flood_run_output` is exactly `depth_raster`, `extent`, and `edge_depth`, the three values of `run_output.Output` since [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]].
It returns null when no run has all three, answers 503 when the database refuses the connection, and answers 404 for any other path.
The names are repeated in `analysis-service/app/server.py`, because the image does not ship `scripts/`, and a test fails when the two lists differ.

## Credentials

The service has three database credentials and no other secret.
The `analysis` service in `compose.yml` has no `env_file` and does not use the Airflow anchor, so the 3Di, Tomorrow.io, and MinIO keys never reach it.
`test/test_analysis_service_compose.py` fails when an `env_file` or one of those keys is added.

| Role | Database | Rights | Created by |
| ---- | -------- | ------ | ---------- |
| `analysis_reader` | `storage-postgres` | `SELECT` on the tables of its list in [[core-output-contract]] | `create_routing_reader_role.py analysis_reader` |
| `analysis_owner` | `storage-postgres` | owns schema `analysis`, and has no right on schema `public` | `create_analysis_schema.py` |
| `analysis_timescale_reader` | `timescaledb` | `SELECT` on `depth_history` and `history_moment` | `create_timescale_reader_role.py` |

Each role has its own variable pair in `.env`: `<ROLE>_USER` and `<ROLE>_PASSWORD`.
The three scripts share the statements of `scripts/database/roles.py` and run again without change.
`compose.yml` requires every password with `:?`, so every `docker compose` command fails until `.env` has all three.
The owner and TimescaleDB credentials are in the environment, but the service does not use them yet.

## Checked on the server

On 2026-10-12 at 13:03 +07, from the container with its own credentials: `/health` returned `20261011T001500`, `analysis_reader` was denied a write to `flood_road_values`, `analysis_owner` created a table in schema `analysis` and was denied one in `public`, `analysis_timescale_reader` was denied a write to `depth_history`, and the environment held no 3Di, Tomorrow.io, MinIO, or `ORG_UUID` variable ([[US-109-run-an-analysis-service-in-its-own-container|US-109]]).

## Rollout

Add the passwords to `.env`, pull the branch, run the two role scripts in the worker with the passwords passed to `docker exec` (the worker reads `.env` only when it is created), and build and start the service from the server desktop, because `docker build` over SSH fails.
