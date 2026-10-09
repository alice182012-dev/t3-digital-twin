---
date_drafted: 2026-10-07
type: user-story
us_id: "US-087"
story_label: "2"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P3
estimate: S
sprint: 12
subsystem: core-output
related: ["[[EP-12-core-output-hygiene]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Make `test_flood_areas.py` run without hand-set paths, and run it in CI"
---

# US-087 Make `test_flood_areas.py` run without hand-set paths, and run it in CI

As a maintainer, I want the routing flood-area test to run the same way everywhere, so a regression in
`derive_areas()` and `build_custom_model()` fails a check and does not wait for someone to remember the setup.
Given `floodmap/graphhopper-flood-road/backend/test_flood_areas.py`, when it runs without `PYTHONPATH`, then it fails
with `ModuleNotFoundError: create_flood_road_tables`. It needs two directories on the path
(`floodmap/graphhopper-flood-road/scripts` for `flood_utils`, and `scripts/database` for `create_flood_road_tables`)
and a PostGIS database in `FLOOD_TEST_DSN`. With the path set and no DSN, it prints `FLOOD_TEST_DSN unset; skipping`
and exits as a pass. The only CI workflow, `.github/workflows/java-module.yml`, never runs it.
Checked on 2026-10-07 on the Mac with `python3 -I`: the documented path (`PYTHONPATH=../scripts:../../../scripts/database`)
imports and skips, and a run without the path fails.
Given the story is done, when CI runs, then a job starts a throwaway `postgis/postgis:15-3.4` service, sets the path
and `FLOOD_TEST_DSN`, and runs the test to a real pass. A test that skips in CI fails the job. The docstring shows one
command that works from the repository root.
The earlier log line said the test "failed at `5e4a314` already". The cause is the missing path, not a change to the
code under test, so check that the test body passes against a real PostGIS before the story closes.
Priority: P3. Status: Done. Estimate: S. Sprint: 12. Dependencies: None. CI needs the repository's GitHub
Actions, which `java-module.yml` already uses.
Evidence: None yet.

## Evidence and details

**Evidence:** None

**Details:**

![[us-087-flood-areas-test-check-output.png|120]]
