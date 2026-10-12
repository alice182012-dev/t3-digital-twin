---
date_drafted: 2026-10-10
type: user-story
us_id: "US-109"
title: "Run an analysis service in its own container"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: In progress
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

## Evidence and details

Fill this when the story reaches `Done`.
A server screenshot of the health response and the three permission checks is the evidence.
