---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-7, edge-depth-table, us-044, graph-hash, reimport]
related: ["[[edge-depth-table]]", "[[edge-depth-table-stories]]", "[[edge-depth-table-format]]", "[[edge-depth-table-publish]]", "[[graphhopper-backend]]", "[[sprint-plan-2]]"]
---

# Plan: the graph re-import page and the stale-table check (US-044)

## Context

Acceptance, from [[edge-depth-table-stories]] Story E6. Given a re-imported graph, when a person follows the page, then the export, the table, and the hash are regenerated together. Given the old table, when a request arrives, then the reader refuses it before a route is served, and the log names the mismatch. The page is a concept page under `artifacts/docs/concepts/`.

GraphHopper edge ids change on every re-import, so a table built for the old graph points depth at the wrong roads on the new one. The graph hash in the table header is the guard.

## What can be built now, and what cannot

The second sentence of the acceptance is about a request reaching the routing engine. The Java reader that checks the hash is `US-043` (Sprint 8), and the engine that uses it is `US-050` and `US-052` (Sprints 8 and 9). That behavior cannot be built or shown in Sprint 7. `US-043` already carries the same criterion: "Given a table for a different graph hash, then the reader refuses it and names both hashes."

What `US-044` can deliver now, and prove on the server:

1. **The page**, `graph-reimport-procedure.md`: when a re-import is needed, the commands in order, how to check each step, what is stale in between, and how to roll back.
2. **A guard for the Python readers**: `require_graph_hash` and `read_latest_table_for_graph` in `edge_depth_table.py` raise `StaleTableError`, whose message names both hashes, the run, and the page. The departure timeline will use it.
3. **A freshness check for the operator**: `scripts/edge_depth/check_tables.py` compares the hash of the export folder, of `graph_edge`, of the `latest` table and of the other kept tables, and optionally the hash of the live graph that `export-edges.sh` prints. It names every mismatch and exits 1 when `latest` is stale.

The request-time refusal in the Java engine is left to `US-043`. This split is recorded in the story, and I ask the user to confirm it.

## Steps

Tests first at every step.

1. `StaleTableError`, `require_graph_hash`, `read_latest_table_for_graph`. Tests: a matching hash passes, a different hash raises with both hashes and the run in the message, the error is logged, and a missing pointer is not reported as stale.
2. `check_tables.py`: a pure `check(...)` over folders and hashes, and a command line. Tests: all hashes equal, the table older than the export, the export older than the live graph, `graph_edge` behind (self-healing, not stale), older kept tables with an old hash (not read, not stale), no table, no export.
3. The page, with the procedure taken from the vault (wipe `/data/graph-cache/*`, force-recreate `graphhopper` over SSH with `--no-deps`) and from the scripts that exist.
4. `server_check.sh` runs `check_tables.py` against the real folders, and shows the stale case by giving it a different hash.
5. Docs, sprint plan, `TODOS.md`.

## Not in this story

- A real re-import of the live graph. It restarts the routing service, and nothing here needs it. The page says how, and the stale case is shown with a different hash.
- The Java refusal at request time (`US-043`, `US-050`, `US-052`).

## Status history

- **2026-10-05, active.** Plan written at the start of `US-044`. The Java half of the acceptance belongs to `US-043`, so this story builds the page, the Python guard and the operator check.
- **2026-10-05, active.** Steps 1 to 5 built and tested: the guard in `edge_depth_table.py`, `check_tables.py` with 10 tests, the page, and `server_check.sh` step 6 (a fresh case and a stale case). 99 tests pass. Left: the server run, and the user's confirmation of the split with `US-043`.
