---
date: 2026-10-01
type: plan
branch: front-end-according-to-mock-up
status: done
tags: [plan, sprint-5, routing, edge-depth-table, us-040, us-046, us-047, us-034]
related: ["[[sprint-plan-2]]", "[[sprint-plan]]", "[[2026-10-01]]", "[[time-aware-routing-engine-stories]]", "[[edge-depth-table-stories]]", "[[carried-over-backlog]]", "[[us-037-narrow-the-per-run-critical-path]]", "[[edge-depth-table]]", "[[edge-depth-table-format]]"]
---

# Plan: Sprint 5, baselines, reference, table format, and the backend soak

## Context

Sprint 5 of [[sprint-plan-2]] has four rows and no dependency on another sprint. The user started it on 2026-10-01, 18 days before its planned start of 2026-10-19, while `US-037` of Sprint 4 was still measuring ([[us-037-narrow-the-per-run-critical-path]]). The sprint goal is that every later story has a real baseline and a reference to compare against, the depth-table format is fixed, and the current backend has soaked before the engine builds on it.

## Does US-037 block Sprint 5?

No row lists `US-037` as a dependency. Two rows share the server with the pipeline, so the knob that `US-037` changes can disturb them.

| Row | Effect of `US-037` | Order |
| --- | ------------------ | ----- |
| `US-046` | The p50 and p95 of `POST /route` depend on the CPU load of the shared host. The tile build and the depth calculation load it now. | Measure latency after the `US-037` knob settles. The edge count, the image revision, and the step length do not depend on load, so they can go first. |
| `US-047` | None. It runs locally in `marie-curie/` against a throwaway database. | Any time. |
| `US-040` | None. It is a file format and a Python module. | Any time. |
| `US-034` | A redeploy of the worker does not restart the backend, but a changed knob changes the load the soak runs under. A 48-hour clock that starts before the knob settles spans two configurations. | Start the clock after the `US-037` knob settles. |

## Order of work

1. `US-040` first. It is a pure module with no server dependency, and Sprint 6 and 7 stories read its format.
2. `US-047` next, locally.
3. `US-046` partly now (edge count, image revision, step length), and its latency numbers after `US-037` settles.
4. `US-034` last. Its 48-hour clock starts after `US-037` is `Done`, so the soak sees one configuration.

## US-040 design

The data shape is one immutable table per run, indexed by GraphHopper edge id. GraphHopper numbers edges densely from 0, so the edge id is the row index and the file stores no id column. The format reference is [[edge-depth-table-format]].

1. A header with a version, the graph hash, the run name, the step times in UTC, and the edge count.
2. A body of one unsigned 16-bit depth in centimetres for each edge and step, edge-major, so the engine reads all steps of one edge from one contiguous run.
3. All integers are little-endian, so the Java reader (`US-043`) reads the same bytes without a conversion library.
4. The graph hash and the run name are length-prefixed UTF-8 strings. The hash algorithm belongs to the export story (`US-039`), so the format does not fix its length.
5. The reader refuses a wrong magic, a wrong version, and a body whose size differs from the header's counts, in either direction.
6. `latest` is a text file in the table directory with the current table's file name. `US-042` owns the atomic publish and the retention of three runs, so `US-040` only reads and writes the pointer.

The module is `scripts/edge_depth/table.py`, next to `scripts/flood_metrics/`, with its tests beside it. A literal-bytes test pins the format, so a later change to it fails a test instead of silently breaking the Java reader.

## Steps

1. Write the failing tests for `US-040`, then the module, then the format page.
2. Record the Sprint 5 start in [[sprint-plan-2]], the `TODOS.md` rollover, and the epic files.
3. Build `US-047`, then the load-independent part of `US-046`.
4. After `US-037` is `Done`, record the latency baselines for `US-046` and start the `US-034` soak.

## Status history

- **2026-10-01, active.** Plan written. Sprint 5 started on 2026-10-01 at the user's request. `US-037` is the one open Sprint 4 row and blocks no Sprint 5 row.
- **2026-10-01, active.** `US-040` and `US-047` are `Done`. `US-047` lives in `scripts/routing_reference/` and not in `marie-curie/`, so the engine stories can reuse it. It uses no PostGIS, since the scenarios assign depth per edge. Next is the load-independent part of `US-046`.
- **2026-10-01, active.** `US-046` is `In progress`: edge count, source revision, and step length and count are recorded. The graph has 67,833 edges and a run has 8 steps, so two PRD assumptions were corrected and the reference's scenarios use 8 steps. The latency numbers and the `US-034` clock wait for the `US-037` knob.
- **2026-10-02, active.** `US-037` is `Done`, so both held rows moved. `US-046` is `Done`: the p50 and p95 of `POST /route` are in [[routing-not-time-aware]], measured on the server after the knob settled. `US-034` is `In progress`. The user gave the soak start as 2026-10-02 00:45 +07, which is the first on-time run after the cold start, so the 48 hours end on 2026-10-04 00:45 +07. `scripts/backend_soak/` holds the tooling and `run_soak.sh` gives the verdict. Next is that verdict after the window ends.
- **2026-10-02, active.** The user stopped the pipeline, because the 50 mm/h test rain is not a real event. The `US-034` window of 2026-10-02 00:45 +07 is void, and `US-037` is `In progress` again. `US-063` was added to run both under a replay of a recorded 48-hour rain. Plan: [[us-063-realistic-rain-replay-for-us-037-and-us-034]].
- **2026-10-05, done.** Sprint 5 ended on 2026-10-05, with `US-034` and `US-037` closed on 137 runs at the user's decision and `US-068` carried to the Backlog. The plan is closed.
