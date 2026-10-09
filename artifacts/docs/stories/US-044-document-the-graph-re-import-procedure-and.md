---
date_drafted: 2026-09-29
type: user-story
us_id: "US-044"
story_label: "E6"
epic: "[[EP-08-edge-depth-table]]"
status: Done
priority: P1
estimate: S
sprint: 7
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Document the graph re-import procedure and detect a stale table"
---

# US-044 Document the graph re-import procedure and detect a stale table

As an operator, I want a page that says what to do after a graph re-import, so the table and the graph never
drift apart unnoticed.
Given a re-imported graph, when a person follows the page, then the export, the table, and the hash are
regenerated together. Given the old table, when a request arrives, then the reader refuses it before a
route is served, and the log names the mismatch. The page is a concept page under
`artifacts/docs/concepts/`.
Priority: P1. Status: Done. Estimate: S. Sprint: 7. Dependencies: Story E3 (done).
Split of the acceptance: the page, the Python guard, and the operator check are built here. The refusal at request time is in the Java reader, which is Story E5 (`US-043`, Sprint 8), whose acceptance already says "a table for a different graph hash is refused and both hashes are named", and the engine that serves requests comes with `US-050` and `US-052`. That half cannot be shown in Sprint 7. The user confirmed the split on 2026-10-05.
Evidence: ![[us-044-stale-table-check-server-output.png|700]]
Details:
1. What: the operator page [[graph-reimport-procedure]], a guard for the Python readers (`StaleTableError`, `require_graph_hash`, `read_latest_table_for_graph`), and `scripts/edge_depth/check_tables.py`, which compares the hash of the export folder, `graph_edge`, the `latest` table, the older kept tables, and optionally the live graph.
2. How: tests first (14 new, 99 in `scripts/edge_depth/`). The guard raises an error that names both hashes and the run, and logs it at ERROR. The check treats a `latest` table of another graph as stale, an export of another graph than the live one as a problem, and `graph_edge` behind the export, and older kept tables of the old graph, as not problems (the next build reloads the first, and retention removes the second). The page takes its commands from the scripts that exist and from the earlier wipe-and-recreate of the graph cache. `server_check.sh` runs the check twice on the real folders.
3. Why: edge ids change on every re-import, and a table of the old graph puts depth on the wrong roads of the new one. An operator needs to know what to do, and to see that it worked.
4. Effect: on the server on 2026-10-05, with the real export, `graph_edge` and `latest` table all on hash `8c13d884...`, the check says `FRESH`. Against a hash that is not the live one it says `STALE`, names both full hashes and the run, and exits 1. Republishing the same table leaves `latest` unchanged. `US-043` can reuse the wording of the refusal, and `US-045` can use the check in its proof.
5. Limits: the refusal at request time is the Java reader (`US-043`) and the engine (`US-050`, `US-052`), so that half of the acceptance is not shown here. A full re-import of the live graph was not rehearsed, because it takes routing down, and the stale case was shown with a different hash. The page's step 1 and 2 commands follow earlier practice and are not run end to end. The evidence image is rendered from output the user pasted.
