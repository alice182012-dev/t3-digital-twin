---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-8, java, edge-depth-table, us-043, hash-check, reload]
related: ["[[edge-depth-table]]", "[[edge-depth-table-stories]]", "[[edge-depth-table-format]]", "[[edge-depth-table-publish]]", "[[graph-reimport-procedure]]", "[[graphhopper-backend]]", "[[sprint-plan-2]]"]
---

# Plan: the Java reader of the edge depth table (US-043)

## Context

Acceptance, from [[edge-depth-table-stories]] Story E5. Given the shared fixture, when the Java reader reads it, then it returns the same values as the Python reader for every edge and step. Given a table for a different graph hash, then the reader refuses it and names both hashes. Given a new `latest` pointer, then the engine memory-maps the new table within 30 seconds, and a request in flight finishes on the old table.

This is also where the request-time refusal that `US-044` handed over is built. The engine that serves requests (`US-050`, `US-052`) will call this reader.

## What is already there

1. The format, `edge-depth-table-format`, and its Python reader and writer (`scripts/edge_depth/edge_depth_table.py`), with the wording of the refusal (`StaleTableError`).
2. The module `java/time-aware-routing/` (Maven, Java 17, built in CI and in the Docker `test` stage) and `ExportEdges`, whose hash algorithm the engine needs to compute the hash of the graph it has loaded.
3. The tables on the Docker volume `edge-depth-tables`, with an atomic `latest` pointer. The Python publish check proved a reader in its own process, and left open that a reader in a second container is not seen yet.

## Design

1. **`EdgeDepthTable`**: one table file, memory-mapped read-only, little-endian. `depthCm(edgeId, step)`, and the header (graph hash, run name, step times, edge count). It checks what `read_table` checks: magic, version, a cut-off header, a body of the wrong size, text that is not UTF-8, step times that do not increase. A bad file raises `TableFormatException`.
2. **The refusal**: `requireGraphHash(expected)` raises `StaleTableException`, with the same words as the Python error, naming both hashes and the run. It is not a `TableFormatException`: a damaged file is a bug, and an old table is an unfinished re-import.
3. **`LatestTableSource`**: watches a table folder. `current()` returns the table the engine uses, or nothing. `refresh()` reads `latest`; if the name changed it maps the new table and checks its hash against the hash of the loaded graph. A new table that does not read, or is for another graph, is refused and logged at ERROR with both hashes, and the table in use stays. At start with no valid table, `current()` is empty, and the engine falls back to today's model.
4. **A request keeps its table.** A request takes the `EdgeDepthTable` reference once, at its start, and uses it to the end. A swap changes what the next request gets. The old mapping stays valid while it is referenced.
5. **Reload within 30 seconds.** A daemon thread calls `refresh()` every 5 seconds by default (a constant, with a test that it is at most 30). Tests use a short interval.
6. **The hash of the loaded graph**: `GraphHash.compute(BaseGraph)`, the algorithm of `ExportEdges`, extracted so both use one copy. A test checks that it equals the hash in `graph.json`, and that the hash of the Andorra graph does not change.
7. **One fixture, two readers.** A file of 3,000 edges by 9 steps with values that include 0 and 65,535, and a JSON file with its header and every value, written by a Python generator. Both copies live in the Java module's test resources, because the Docker build sees only that folder. A Python test regenerates the bytes and checks both copies, and reads the file with the Python reader.
8. **A command for the server**: `EdgeDepthTableTool` reads a folder (read-only), prints the header and chosen values, checks a graph hash, and can `--watch` and count reads and failures. `reader-check.sh` runs it in the time-aware image with the volume mounted read-only: the real table against the live graph's hash, the stale case, and a reader in a second container while the Airflow worker publishes into a scratch folder.

## Steps

Tests first at every step.

1. The fixture generator and the Python test.
2. `EdgeDepthTable`, the exceptions, and their tests on the fixture and on damaged copies of it.
3. `LatestTableSource` and its tests: load, refuse, keep the old table, reload, in flight, missing pointer.
4. `GraphHash`, `ExportEdges` uses it, and the Andorra hash is unchanged.
5. `EdgeDepthTableTool` and `reader-check.sh`.
6. Docs, sprint plan, `TODOS.md`.

## Not in this story

- Calling the reader from the routing engine, and the use of depth in a search (`US-050`, `US-052`).
- Compose changes that mount the volume into the `graphhopper` service (`US-052`).

## Risks

- **Mapped files and deletion.** Retention can delete a table that a request still has mapped. On Linux the mapping stays valid. A test covers it, and the page says the volume must be Linux.
- **A refused table at the first start** leaves the engine without depth. That is the intended fallback, and the log is the signal.

## Status history

- **2026-10-05, active.** Plan written at the start of `US-043`.
