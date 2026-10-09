---
date_drafted: 2026-10-10
type: epic
epic_id: "EP-18"
theme: routing
status: active
subsystem: floodmap-backend, airflow-pipeline, routing
tags: [epic, routing, graphhopper]
related: ["[[PRD-003-edge-depth-table|archived PRD-003]]", "[[PRD-004-time-aware-routing-engine|archived PRD-004]]", "[[sticky-c-lite-routing]]", "[[graphhopper-backend]]", "[[flood-on-roads]]", "[[edge-depth-table-format]]", "[[routing-first-consumer-contract]]", "[[decision-log]]"]
---

# EP-18 Time-aware routing engine

## Goal

`POST /route` judges each road at the time the traveller reaches it. The engine uses an edge depth table built for each run, applies sticky closure, and routes all four modes (`motorbike`, `car`, `truck`, `foot`). The recommended route avoids the precaution depth, and the hard-limit route stays as a second option ([[decision-log|D-021]]). When no route exists, the client shows when one opens.

## Why

The old route judged every road at one forecast step. A road that is dry at that step and floods 10 minutes later passed, so a traveller could drive into water ([[BL-011-routing-not-time-aware|BL-011]]). That is a safety fault, not a tuning issue, and GraphHopper cannot fix it alone because its search carries no arrival time. The archived [[PRD-003-edge-depth-table|PRD-003]] and [[PRD-004-time-aware-routing-engine|PRD-004]] hold the full requirements.

## Dependencies and assumptions

- Depth is stored for each GraphHopper `edge_id` and forecast step, tagged with a graph hash. A reader refuses a table with another hash.
- The engine keeps sticky closure ([[decision-log|D-023]]). The margin is 10 minutes, fixed on the server.
- The flag `TIME_AWARE_ROUTING` restores the old behavior when off. A missing or mismatched table falls back to the old single-step model and says so.
- The edge export needs a Java toolchain. Java tests run on GitHub Actions.

## Definition of done

Run each check on the server.

1. Given the synthetic corridor and four scenarios, when `POST /route` runs for `motorbike` and `car`, then no route crosses an edge that is closed at arrival.
2. Given a real run, when a route departs inside it, then the route avoids every edge that floods before arrival and the response names the run.
3. Given a request with a `valid_time` before now, then the departure step is the step that contains now.
4. Given the flag off, then the response equals the body from before this work.
5. Given a table for another graph hash, then the backend falls back, sets the fallback flag, and logs both hashes.
6. Given a route that opens at 18:00, when a request at 17:00 finds no connection, then the alert shows 18:00.
7. Given short, medium, and long trips, then p50 and p95 of `POST /route` stay within 2 times the baseline.

## Risks and open questions

- The image is ours to keep working, because it is built from our module and a GraphHopper upgrade can break it. The version stays pinned.
- The fallback brings back the old fault. The response flag and the frontend message keep it visible.
- Whether `TIME_AWARE_ROUTING` stays on for good is the product owner's decision (see the current sprint file).
- [[BL-026-sticky-closure-clock-anchored-at-floored-departure|BL-026]] is fixed in code by `US-096`. [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]] is `resolved`.

## Stories

```dataview
TABLE title AS "Story", kind AS "Kind", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE contains(string(epic), "EP-18")
SORT file.name ASC
```

## Status history

- **2026-10-10, active.** Created from the Scrum adoption ([[decision-log|D-024]]). It merges the archived epics `EP-08`, `EP-09`, `EP-10`, and `EP-16`, and takes `US-034` from `EP-07` and `US-022`.
