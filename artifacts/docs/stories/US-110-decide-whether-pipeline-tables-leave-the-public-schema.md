---
date_drafted: 2026-10-10
type: user-story
us_id: "US-110"
title: "Decide whether pipeline tables leave the public schema"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: spike
priority: P3
estimate: S
sprint: 13
subsystem: storage, core-output
source_ideas: []
related: ["[[core-output-contract]]", "[[storage-backend-django-layer]]"]
tags: [user-story, spike]
---

# US-110 Decide whether pipeline tables leave the public schema

As a developer, I want to know whether the pipeline tables should leave schema `public`, so Django migrations and the pipeline DDL scripts stop sharing one schema.

**Question.**
What does it cost to move the pipeline tables into their own schema in `minio_custom`, and what breaks if they stay?

**Timebox.**
Half a sprint, on a copy of the database in `marie-curie/`.

The spike lists every table in `public` by owner (Django migrations or `scripts/database/`).
It then finds what a move changes: the grants in `create_routing_reader_role.py` (which name `public`), the queries in `floodmap/graphhopper-flood-road/backend/` and `scripts/` that do not qualify a schema, `test_core_contract.py`, and the connection `search_path`.
It also tests whether `python manage.py migrate` ever touches a pipeline table.

Given the spike on a copy of the server database, when it ends, then the story holds the table list by owner, the list of files a move changes, and a decision `D-nnn` that says move now, move later with a trigger, or stay.

Dependencies: None.

## Status history

- **2026-10-10, draft.** Ready: the question is stated, it has an estimate, and the answer is a decision.
- **2026-10-12, Sprint 13.** Picked at Sprint 13 planning at S (2 points). It has no dependency.

## Evidence and details

Fill this when the spike ends.
A spike records its measured result instead of a screenshot.
