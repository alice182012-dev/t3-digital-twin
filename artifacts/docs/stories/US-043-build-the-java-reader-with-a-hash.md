---
date_drafted: 2026-09-29
type: user-story
us_id: "US-043"
story_label: "E5"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: M
sprint: 8
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Build the Java reader with a hash check and reload without restart"
---

# US-043 Build the Java reader with a hash check and reload without restart

As the routing engine, I want to read the newest table and refuse a wrong one, so a graph change never
serves stale depth.
Given the shared fixture, when the Java reader reads it, then it returns the same values as the Python
reader for every edge and step. Given a table for a different graph hash, then the reader refuses it and
names both hashes. Given a new `latest` pointer, then the engine memory-maps the new table within 30
seconds, and a request in flight finishes on the old table.
Dependencies: Stories E2, R4.
Evidence: ![[us-043-java-reader-server-output.png]]
Details:
1. What: the Java reader of the edge depth table in `java/time-aware-routing/`: `EdgeDepthTable` (memory-mapped, read-only), `LatestTableSource` (follows `latest`), `GraphHash` (extracted from `ExportEdges`), `EdgeDepthTableTool`, and `reader-check.sh`.
2. How: tests first, 38 new module tests (57 in all). A shared fixture, `scripts/edge_depth/golden_fixture.py`, is read by Python and Java, and all 27,000 values match. Damaged files are refused with the Python reader's causes. A table for another graph is refused with both hashes named, in the Python wording. `LatestTableSource` logs a refused table at ERROR and keeps the valid one, polls every 5 s (never over 30 s), and a caller that holds a table keeps it. The hash of the tiny test graph is pinned, so the `GraphHash` extraction cannot change it. Skipping the hash check fails 2 tests.
3. Why: edge ids change on every graph re-import, so the engine must refuse a table of another graph at request time, and must pick up each new run without a restart.
4. Effect: on the server, in a second container with the volume and the live graph cache mounted read-only, the real table (run `20261005T120000`, 67,833 edges, 8 steps) read and matched the live graph hash `8c13d884...`. Against another hash it said `STALE`, named both, and exited 1. While the reader ran, the worker published a new `latest` into a scratch folder, and the reader loaded it 8 s later with no restart (poll every 5 s, limit 30 s). The real `latest` was not touched. `US-050` and `US-052` can call `LatestTableSource.current()`, and `US-045` can reuse `reader-check.sh`.
5. Limits: the in-flight request keeping its old table is shown in a unit test, not on the server. The engine does not call the reader yet (`US-050`, `US-052`). The reload was shown with copies of one table under two names, so the run name did not change. The evidence image is rendered from output the user pasted.
