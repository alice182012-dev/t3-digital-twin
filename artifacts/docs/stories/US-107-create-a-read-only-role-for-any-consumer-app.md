---
date_drafted: 2026-10-10
type: user-story
us_id: "US-107"
title: "Create a read-only role for any consumer app"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: story
priority: P2
estimate: S
sprint: 
subsystem: storage, core-output
source_ideas: []
related: ["[[core-output-contract]]", "[[US-072-run-the-routing-backend-on-a-read|US-072]]"]
tags: [user-story]
---

# US-107 Create a read-only role for any consumer app

As a developer of a new consumer application, I want my own read-only database role, so my application reads the contract tables it needs and nothing else.

`scripts/database/create_routing_reader_role.py` makes one role, `routing_reader`, with `SELECT` on every table of the contract page.
Change it to take a role name and read that role's table list from a section of `core-output-contract.md`.
The section names each role and its tables.
`routing_reader` keeps the same tables as today, so `floodmap-backend` does not change.
A second role, `analysis_reader`, is added to the page and gets the tables an analysis reads.
The password of each role comes from its own variable in `.env`.

Given the script run on the server for both roles, when a session connects as `analysis_reader`, then `SELECT` works on its tables, an `INSERT` fails with a permission error, and a `SELECT` on `road_segment`, which is not in its list, fails with a permission error.
Given the same run, then `floodmap-backend` still answers `POST /route` as `routing_reader`, and `test_reader_role.py` passes for both roles.

Dependencies: None.

## Status history

- **2026-10-10, draft.** Ready: it passes the INVEST check.

## Evidence and details

Fill this when the story reaches `Done`.
A server screenshot of the three permission checks is the evidence.
