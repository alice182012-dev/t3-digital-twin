---
date_drafted: 2026-10-13
type: user-story
us_id: "US-137"
title: "Make the tests of test/ pass without a 3Di client of the pinned version"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Ready
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: testing
source_ideas: []
related: ["[[test-dataset]]", "[[US-128-run-the-test-suites-against-the-test-databases|US-128]]"]
tags: [user-story]
---

# US-137 Make the tests of test/ pass without a 3Di client of the pinned version

As a developer, I want `python3 -m pytest test/` to give no failure and no collection error on the Mac, so a red run means a real defect.

On 2026-10-13 the suite gave 10 failures and 2 collection errors on the Mac, on a clean `modular`.
Three defects cause them.
First, the Mac has `threedi-api-client` 4.2.6 and `requirements.txt` pins 5.0.5, so `create_simulation.py` cannot import `TimedSavedState`, and 10 tests of `test_flood_rain_gate.py` and `test_threedi_auth_alert.py` fail.
Second, the tests do not put `scripts/` on `sys.path`, so `test_calculate_depth.py` cannot import `depth_inputs`, and the same tests run in the worker only with `PYTHONPATH=scripts`.
Third, `test/test_threedi_state_test.py` is a manual script that creates two real simulations on 3Di (the file says so), and its name makes pytest collect and import it.
In the worker, with the pinned client and `scripts/` on the path, the tests of the first two groups pass (6, 4, and 2 tests).

The story adds a `test/conftest.py` that puts `scripts/` on the path and stands in for the names that the installed client lacks, and a test that fails visibly (a skip with the reason) when the installed client differs from the pin.
It moves the manual script out of the test folder, so pytest does not collect it.

Given the Mac with `threedi-api-client` 4.2.6, when `python3 -m pytest test/` runs, then no test fails, no module fails to collect, and one test is skipped with the reason that names the installed and the pinned version.
Given the worker with the pinned client, when the same tests run, then they pass and nothing is skipped.
Given `scripts/threedi_state_check.py` (the moved script), then `python scripts/threedi_state_check.py` still runs as before and pytest does not collect it.

Dependencies: None.

## Status history

- **2026-10-13, draft.** Found when [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] changed the tests of `test/`. The owner asked on the same day to fix the failing tests first.
- **2026-10-13, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request. It is `Ready` and not `In progress`, because [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] and [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] already fill the two places.

## Evidence and details

Fill this when the story reaches `Done`.
