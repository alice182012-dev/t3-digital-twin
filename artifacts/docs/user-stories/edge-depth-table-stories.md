---
date_drafted: 2026-09-29
type: user-story
us_ids: ["US-039", "US-040", "US-041", "US-042", "US-043", "US-044", "US-045"]
status: draft
subsystem: airflow-pipeline, floodmap-backend
source_ideas: ["[[sticky-c-lite-routing]]"]
related: ["[[edge-depth-table]]", "[[sprint-plan-2]]", "[[sprint-plan-3]]", "[[time-aware-routing-engine-stories]]", "[[flood-on-roads]]"]
tags: [user-story, epic, airflow, graphhopper, raster, edge-id, sprint-5, sprint-6, sprint-7, sprint-8]
---

# Epic: edge depth table

The requirements are in [[edge-depth-table]]. The engine that reads the table is in
[[time-aware-routing-engine-stories]]. The order of work is in [[sprint-plan-2]].

Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic
shape in [[user-story-types]]. Sprint numbers continue from [[sprint-plan]]. A story reaches `Done` only with
a screenshot and numbered details, recorded here and in `sprint-plan-2.md`.

- **Story E1 (US-039): Export the graph's edges.**
  As the table builder, I want every GraphHopper edge with its id, geometry, and a graph hash, so depth can
  be sampled per edge.
  Given the built graph on the server, when the export command runs, then it writes one row per edge with the
  edge id and its geometry in EPSG:4326, plus a hash of the graph build, and the row count equals the graph's
  edge count.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 6. Dependencies: Story R4.

- **Story E2 (US-040): Define the table format and write the Python reader and writer.**
  As an engineer, I want one documented file format with a reference reader and writer, so the Java engine and
  the Python timeline read the same bytes.
  Given a fixture of a few thousand edges and 9 steps, when the writer writes it and the reader reads it back,
  then every edge and step returns its value. The header holds a version, the graph hash, the run name, the
  step times, and the edge count. The reader refuses a file with a wrong version or a truncated body.
  A pointer file named `latest` names the current table.
  Priority: P0. Status: Done. Estimate: S. Sprint: 5. Dependencies: None.
  Evidence: ![[us-040-table-check-output.png|700]]
  Details:
  1. What: file format version 1 for one run's depth by edge id, a Python reader and writer, and the `latest` pointer file. The format is in [[edge-depth-table-format]].
  2. How: `scripts/edge_depth/edge_depth_table.py`. A header holds the version, the graph hash, the run name, the step times, and the edge count. The body holds one `uint16` depth in centimetres per edge and step, edge-major, so the edge id is the row index. Tests came first (25 tests, 13 subtests), and one test pins the layout to a literal byte string. The reader refuses a wrong magic, a wrong version, a cut-off header, and a body that is too short or too long.
  3. Why: the Java engine and the Python timeline must read the same bytes, and the Sprint 6 and 7 stories build on one fixed format.
  4. Effect: on a Mac, a table of 2,000,000 edges and 9 steps is 36.0 MB, the writer takes 1.3 s, and the reader opens it in 0.01 s. `US-043` (the Java reader) starts from the literal-bytes test. The atomic publish and the retention of 3 tables stay with `US-042`. The hash guard stays with `US-043` and `US-044`. The hash algorithm is open for `US-039`, and the file extension is open for `US-041`.

- **Story E3 (US-041): Build the Airflow task that writes each run's table.**
  As the routing engine, I want one depth value per edge and step for each run, so it can look up depth by
  edge id.
  Given a real run and the export from Story E1, when the task runs after `9b_load_depth_raster`, then it
  samples the raster tiles along each edge, stores the deepest 1 m sample in centimetres, tags the file with
  the graph hash, and reports its duration and size. For 20 hand-picked edges the values equal a direct
  `ST_Value` reading. An edge outside the model reads 0.
  Priority: P0. Status: Not started. Estimate: L. Sprint: 7. Dependencies: Stories E1, E2.

- **Story E4 (US-042): Publish the table atomically and keep the newest three runs.**
  As a reader, I want a new table to appear in one step, so I never read a half-written file.
  Given a reader that polls in a loop, when the task publishes a table, then the reader sees the old table or
  the new one and never a partial file. Given four runs, when the fourth publishes, then the oldest is
  removed. A failed task leaves the previous `latest` in place and does not block the DAG.
  The story also picks the storage, a volume or MinIO, and records why.
  Priority: P0. Status: Not started. Estimate: S. Sprint: 7. Dependencies: Story E3.

- **Story E5 (US-043): Build the Java reader with a hash check and reload without restart.**
  As the routing engine, I want to read the newest table and refuse a wrong one, so a graph change never
  serves stale depth.
  Given the shared fixture, when the Java reader reads it, then it returns the same values as the Python
  reader for every edge and step. Given a table for a different graph hash, then the reader refuses it and
  names both hashes. Given a new `latest` pointer, then the engine memory-maps the new table within 30
  seconds, and a request in flight finishes on the old table.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 8. Dependencies: Stories E2, R4.

- **Story E6 (US-044): Document the graph re-import procedure and detect a stale table.**
  As an operator, I want a page that says what to do after a graph re-import, so the table and the graph never
  drift apart unnoticed.
  Given a re-imported graph, when a person follows the page, then the export, the table, and the hash are
  regenerated together. Given the old table, when a request arrives, then the reader refuses it before a
  route is served, and the log names the mismatch. The page is a concept page under
  `artifacts/docs/concepts/`.
  Priority: P1. Status: Not started. Estimate: S. Sprint: 7. Dependencies: Story E3.

- **Story E7 (US-045): Prove the table on the server.**
  As the team, I want measured build time, size, and spot checks on the server, so the estimates become
  numbers.
  Given a real run on the server, when the task runs, then the report gives the edge count, the file size, and
  the build time for the run, and 20 edges match `ST_Value`. The story records the numbers in
  [[edge-depth-table]] and replaces the guessed size. If the build time exceeds the limit the user sets, the
  story records a blocker.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 8. Dependencies: Stories E3, E4. Gate: the user
  sets the build-time limit before this sprint.

## Status history

- **2026-09-29, draft.** Written from [[edge-depth-table]]. No story has started.
- **2026-10-01, draft.** Story E2 (`US-040`) is `Done`: the Python reader and writer pass 25 tests, and a table of 2,000,000 edges and 9 steps is 36.0 MB. Output rendered as `us-040-table-check-output.png`. The format is [[edge-depth-table-format]].
