---
date_drafted: 2026-10-10
type: user-story
us_id: "US-109"
title: "Run an analysis service in its own container"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Reviewed
kind: story
priority: P2
estimate: M
sprint: 13
subsystem: analysis, compose
source_ideas: []
related: ["[[core-output-contract]]", "[[timescaledb-schema]]"]
tags: [user-story]
---

# US-109 Run an analysis service in its own container

As a developer of the analysis application, I want a service with its own image, its own dependencies, and its own database schema, so I can add libraries and tables without touching the Airflow image or the pipeline tables.

The service builds from its own folder with its own requirements file and installs nothing into the Airflow `Dockerfile`.
It connects to `storage-postgres` as `analysis_reader` ([[US-107-create-a-read-only-role-for-any-consumer-app|US-107]]) and to `timescaledb` as a new read-only role.
It owns a schema `analysis` in `storage-postgres` with its own owner role, which is the only place it writes.
The first endpoint, `GET /health`, returns the newest `run_ts` that has all four rows in `flood_run_output` ([[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]]).
Each credential has its own variable in `.env.example`.
The service has no other secret, so the 3Di and Tomorrow.io keys are not in its environment.

Given the service running on the server, when `GET /health` is called, then it returns that `run_ts`.
Given a connection from the service, then a write to `flood_road_values` fails with a permission error, a write to a table in schema `analysis` works, and `printenv` in the container shows no `THREEDI_API_KEY` and no `TOMORROW_API_KEY`.
Given `git diff` of the story, then `Dockerfile` and `requirements.txt` at the repo root are unchanged.

Dependencies: US-107, US-108.

## Status history

- **2026-10-10, draft.** Not started: it waits for `US-107` and `US-108`. It is rated M. Split the Timescale role into its own story if the sprint needs it smaller.
- **2026-10-12, Ready.** Both dependencies are `Done`: [[US-107-create-a-read-only-role-for-any-consumer-app|US-107]] and [[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]]. The story passes the INVEST check. Picked for Sprint 13 at M (3 points), and the Timescale role stays in this story.
- **2026-10-12, In progress.** Started after [[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]] was accepted. The build is the folder `analysis-service/`, two role scripts, and a service in `compose.yml` with an explicit environment block.
- **2026-10-12, Reviewed.** Built, pushed, and deployed on the server on 2026-10-12, with the checks in details items 9 and 10. It waits for the server screenshot and the owner's acceptance.

## Evidence and details

**Evidence:** the server capture of 2026-10-12 13:03 +07, from the Mac, and tests on throwaway PostGIS and TimescaleDB containers (removed afterwards).

![[us-109-server-check-output.png|900]]

**Details:**

1. The service is the folder `analysis-service/`: its own `Dockerfile` (python:3.12-slim), its own `requirements.txt` (`psycopg2-binary` only), and `app/server.py`, which is a stdlib `ThreadingHTTPServer` like the routing backend. `GET /health` returns `{"run_ts": ...}` for the newest run whose set of outputs in `flood_run_output` equals the four of `run_output.Output`, or null. A refused connection gives 503, and any other path gives 404. The root `Dockerfile` and `requirements.txt` are unchanged (`git diff` is empty).
2. The service reads `storage-postgres` as `analysis_reader` ([[US-107-create-a-read-only-role-for-any-consumer-app|US-107]]). `scripts/database/create_analysis_schema.py` makes the role `analysis_owner` and schema `analysis`, with no right on schema `public`, and `scripts/database/create_timescale_reader_role.py` makes `analysis_timescale_reader`, which can only `SELECT` `depth_history` and `history_moment`. Both scripts run again without change. A shared `roles.py` holds the common statements, and `create_routing_reader_role.py` uses it with unchanged behavior.
3. The `analysis` service in `compose.yml` has no `env_file` and does not use the Airflow anchor. Its `environment` holds only its own variables. `test/test_analysis_service_compose.py` fails if an `env_file`, a `THREEDI` key, or a `TOMORROW` key is added.
4. Tests on 2026-10-12: 12 offline tests pass, and with throwaway databases the 10 tests of `analysis-service/test` and the 18 of the three role scripts pass (PostGIS 17-3.5 and TimescaleDB 2.30.1). A test of the routing reader grants was already failing on `modular` after the contract change of [[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]], and a separate commit fixed its list.
5. Server state, read only, 2026-10-12: `analysis_reader` exists, schema `analysis` and `analysis_owner` do not, and no `analysis%` role exists in TimescaleDB. `flood_run_output` has the runs `20261011T001500` and `20261011T000000`, each with all four outputs, so `/health` returns `20261011T001500`. `ANALYSIS_READER_PASSWORD` is in the server `.env`, and the two new passwords are not.
6. Rollout order. Compose resolves every variable of the file for every command, so once the branch is pulled, every `docker compose` command fails until `.env` has `ANALYSIS_OWNER_PASSWORD` and `ANALYSIS_TIMESCALE_READER_PASSWORD`. First add both passwords to the server `.env`. Then pull `modular`. Then run `create_analysis_schema.py` and `create_timescale_reader_role.py` in the worker with the passwords passed to `docker exec`, because the worker reads `.env` only when it is created. Then build and start the service from the server desktop, because `docker build` over SSH fails.
7. The service does not use the owner and the TimescaleDB credentials yet. They are in its environment so the permission checks can run from inside the container.
8. Deployed on 2026-10-12 with the owner's go, in the order of item 6. `modular` was pushed (`d100d6e` to `552ca9f`) and pulled by fast-forward, and the owner had added both passwords to the server `.env`. `create_analysis_schema.py` printed that `analysis_owner` owns schema `analysis`, and `create_timescale_reader_role.py` printed that `analysis_timescale_reader` can read `depth_history` and `history_moment`. The owner built the image and started the service from the server desktop (`docker compose build analysis`, then `up -d --no-deps analysis`).
9. The check script `artifacts/docs/stories/evidence/us-109-server-check.sh`, run by the owner from the Mac at 13:03 +07, printed: the container `airflow_new-analysis-1` up on `127.0.0.1:8020`; `GET /health` returning `{"run_ts": "20261011T001500"}`; with the service's own credentials, `analysis_reader` reads `flood_run_output` and is denied a write to `flood_road_values`, `analysis_owner` creates a table in schema `analysis` and is denied one in `public`, and `analysis_timescale_reader` reads `depth_history` and is denied a write; 0 variables named THREEDI, TOMORROW, MINIO, or ORG_UUID in the container environment; and the root `Dockerfile` and `requirements.txt` unchanged against `main`.
10. Checked afterwards, read only: no table `us109_probe` exists and schema `analysis` has no table, because the probes ran in rolled-back transactions. The container stays up, its log shows the health request answered with 200, and no service is in `Created` or `Restarting`.
11. The server screenshot of item 9 is saved as `us-109-server-check-output.png`.
12. Open for `Done`: the owner's acceptance.
