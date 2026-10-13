---
date_drafted: 2026-10-13
type: user-story
us_id: "US-132"
title: "Let the worker run the reader role script"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Not started
kind: story
priority: P3
estimate: S
sprint: 
subsystem: database, airflow-pipeline
source_ideas: []
related: ["[[core-output-contract]]", "[[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]]"]
tags: [user-story]
---

# US-132 Let the worker run the reader role script

As a developer, I want `create_routing_reader_role.py` to run in the Airflow worker, so a deploy needs no manual `GRANT` statements or temporary file copies.

The script imports `core_contract.py` from `floodmap/graphhopper-flood-road/backend` and reads the contract page `artifacts/docs/concepts/core-output-contract.md`.
The worker mounts neither, so on 2026-10-12 the grants were typed by hand ([[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]]), and on 2026-10-13 both files were copied into the worker's `/tmp` for one run.
The story moves the parser and the table lists to a place that the worker mounts, or mounts them, and keeps one copy of each.

Given the worker after a pull, when `python create_routing_reader_role.py routing_reader` runs there, then the role has `SELECT` on each table the contract page lists for it.
Given the script run twice, then the grants are the same.

Dependencies: None.

## Status history

- **2026-10-13, draft.** Found during the server checks of [[SPR-014-finish-the-remaining-backend|SPR-014]]. The owner asked for a story on the same day.

## Evidence and details

Fill this when the story reaches `Done`.
