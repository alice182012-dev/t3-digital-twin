---
date_drafted: 2026-09-29
type: user-story
us_ids: ["US-039", "US-040", "US-041", "US-042", "US-043", "US-044", "US-045", "US-070"]
status: draft
subsystem: airflow-pipeline, floodmap-backend
source_ideas: ["[[sticky-c-lite-routing]]"]
related: ["[[PRD-003-edge-depth-table|edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]]", "[[flood-on-roads]]"]
tags: [user-story, epic, airflow, graphhopper, raster, edge-id, sprint-5, sprint-6, sprint-7, sprint-8]
---

# Epic: edge depth table

The requirements are in [[PRD-003-edge-depth-table|edge-depth-table]]. The engine that reads the table is in
[[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]]. The order of work is in [[SP-02-routing-engine-foundations|sprint-plan-2]].

Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic
shape in [[user-story-types]]. Sprint numbers continue from [[SP-01-prd-and-backlog|sprint-plan]]. A story reaches `Done` only with
a screenshot and numbered details, recorded here and in `sprint-plan-2.md`.

- [[US-039-export-the-graph-s-edges|US-039]] Export the graph's edges. Story E1.
- [[US-040-define-the-table-format-and-write-the|US-040]] Define the table format and write the Python reader and writer. Story E2.
- [[US-041-build-the-airflow-task-that-writes-each|US-041]] Build the Airflow task that writes each run's table. Story E3.
- [[US-042-publish-the-table-atomically-and-keep-the|US-042]] Publish the table atomically and keep the newest three runs. Story E4.
- [[US-043-build-the-java-reader-with-a-hash|US-043]] Build the Java reader with a hash check and reload without restart. Story E5.
- [[US-044-document-the-graph-re-import-procedure-and|US-044]] Document the graph re-import procedure and detect a stale table. Story E6.
- [[US-045-prove-the-table-on-the-server|US-045]] Prove the table on the server. Story E7.
- [[US-070-stop-a-slow-sampling-step-from-holding|US-070]] Stop a slow sampling step from holding the database. Story E8.

## Status history

Story-level progress lines up to 2026-10-10 are in [[EP-08-edge-depth-table-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-29, draft.** Written from [[PRD-003-edge-depth-table|edge-depth-table]]. No story has started.
- **2026-10-05, draft.** Story E6 (`US-044`): the server check passed. With the export, `graph_edge`, and the `latest` table on hash `8c13d884...` the check says `FRESH`, and against another hash it says `STALE`, names both hashes, and exits 1. Evidence: `us-044-stale-table-check-server-output.png`. The status stays `Reviewed` until the user confirms the split with `US-043`.
- **2026-10-05, draft.** Story E6 (`US-044`) is `Done`. The user confirmed the split with `US-043`: the page, the Python guard, and the operator check are closed here, and the refusal at request time in the Java reader is `US-043`'s acceptance. Evidence: `us-044-stale-table-check-server-output.png`.
