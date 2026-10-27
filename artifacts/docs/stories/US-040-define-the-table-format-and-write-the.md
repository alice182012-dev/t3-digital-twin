---
date_drafted: 2026-09-29
type: user-story
us_id: "US-040"
story_label: "E2"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: S
sprint: 5
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Define the table format and write the Python reader and writer"
---

# US-040 Define the table format and write the Python reader and writer

As an engineer, I want one documented file format with a reference reader and writer, so the Java engine and the Python timeline read the same bytes.
Given a fixture of a few thousand edges and 9 steps, when the writer writes it and the reader reads it back, then every edge and step returns its value.
The header holds a version, the graph hash, the run name, the step times, and the edge count.
The reader refuses a file with a wrong version or a truncated body.
A pointer file named `latest` names the current table.
Dependencies: None.
Evidence: ![[us-040-table-check-output.png|700]]
Details:
1. What: file format version 1 for one run's depth by edge id, a Python reader and writer, and the `latest` pointer file.
   The format is in [[edge-depth-table-format]].
2. How: `scripts/edge_depth/edge_depth_table.py`.
   A header holds the version, the graph hash, the run name, the step times, and the edge count.
   The body holds one `uint16` depth in centimetres per edge and step, edge-major, so the edge id is the row index.
   Tests came first (25 tests, 13 subtests), and one test pins the layout to a literal byte string.
   The reader refuses a wrong magic, a wrong version, a cut-off header, and a body that is too short or too long.
3. Why: the Java engine and the Python timeline must read the same bytes, and the Sprint 6 and 7 stories build on one fixed format.
4. Effect: on a Mac, a table of 2,000,000 edges and 9 steps is 36.0 MB, the writer takes 1.3 s, and the reader opens it in 0.01 s.
   `US-043` (the Java reader) starts from the literal-bytes test.
   The atomic publish and the retention of 3 tables stay with `US-042`.
   The hash guard stays with `US-043` and `US-044`.
   The hash algorithm is open for `US-039`, and the file extension is open for `US-041`.
