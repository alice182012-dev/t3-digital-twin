---
date_drafted: 2026-10-06
type: user-story
us_id: "US-074"
story_label: "C4"
epic: "[[EP-10-routing-first-consumer]]"
status: Done
priority: P2
estimate: S
sprint: 11
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-10-routing-first-consumer]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
---

# US-074 Give the vehicle thresholds one owner

As a maintainer, I want `flood_utils.py` owned by routing, with the core importing it by an explicit path, so the
dependency points one way.
Given the thresholds, when the backend, `scripts/flood_metrics/extract_run.py` and the GraphHopper
`td_limit_cm` all read them, then there is one source, the existing test that compares `td_limit_cm` with
`flood_utils` still passes, and the extractor's import works inside the Airflow container (the problem of
[[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]] must not return).
Priority: P2. Status: Done. Estimate: S. Sprint: 11. Dependencies: None.
Evidence: ![[us-074-vehicle-limit-owner-2026-10-07.png]]
Details:
1. `VEHICLE_PROFILES` in `flood_utils.py` is the one owner of the vehicle depth thresholds.
2. `scripts/test_vehicle_limit_owner.py` scans the repo's source files and fails if a second file defines the
   same limits, and the existing test comparing `td_limit_cm` (GraphHopper `config.yml`) with `flood_utils`
   still passes (confirmed earlier re-running `test_time_aware_route.py`'s
   `test_the_limits_equal_the_thresholds_of_flood_utils`).
3. Run on the server (host ADMIN) on 2026-10-07: `test_no_source_file_defines_the_limits_again ... ok`.
4. The Airflow container's import of `flood_utils` ([[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]]) was checked
   unchanged on 2026-10-07.
