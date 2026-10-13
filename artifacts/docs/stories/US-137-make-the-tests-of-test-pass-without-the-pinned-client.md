---
date_drafted: 2026-10-13
type: user-story
us_id: "US-137"
title: "Make the tests of test/ pass without a 3Di client of the pinned version"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
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
- **2026-10-13, Reviewed.** Built and checked on the Mac and in the worker (details items 1 to 4). The owner has not accepted it.

## Evidence and details

**Evidence:** the test counts in details items 2 and 3. No screenshot.

**Details:**

1. `test/conftest.py` puts `scripts/` on `sys.path` and gives a stand-in class to each name that `create_simulation.py` imports from `threedi_api_client.openapi` and the installed client lacks (`Action`, `ApiException`, `FromTemplate`, `TimedSavedState`, `TimeseriesRain`). A real name is never replaced.
   `test/test_environment_matches_requirements.py` compares the installed client with the pin in `requirements.txt`. On a difference it skips with both versions in the reason. On a match it asserts that no stand-in was installed.
   The three test files that need the stand-ins import `conftest`, because `python -m unittest` does not load `conftest.py` and the worker has no pytest.
2. On the Mac (Python 3.14, client 4.2.6), `python3 -m pytest -q test/` gives 129 passed and 1 skipped (the version test), with no failure and no collection error. Two more runs with `-p no:cacheprovider` gave the same. `python3 -m unittest discover -s test` gives 130 tests, OK, 1 skipped.
   Before the change it gave 10 failed and 2 collection errors.
3. In the worker (Python 3.12, client 5.0.5), `python -m unittest discover -s test -p <file>` gives OK for the version test (1 test, not skipped, so no stand-in is installed), `test_flood_rain_gate` (6), `test_threedi_auth_alert` (4), and `test_calculate_depth` (2).
   The other test files need `compose.yml` and the repository layout, which the copy in the worker did not have, so they were not run there.
4. The manual script moved with `git mv` from `test/test_threedi_state_test.py` to `scripts/threedi_state_check.py`, with its docstring and paths adjusted. It creates two real simulations on 3Di, so it was not run. No other file refers to the old path.

