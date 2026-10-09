---
date_drafted: 2026-09-29
type: user-story
us_id: "US-070"
story_label: "E8"
epic: "[[EP-08-edge-depth-table]]"
status: Reviewed
priority: P1
estimate: S
sprint: 10
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
---

# US-070 Stop a slow sampling step from holding the database

As the operator, I want task 9c to analyze the run's tiles first and cancel a step that runs past its limit, so
one slow query cannot starve the runs behind it (blocker [[BL-023-9c-sampling-step-runs-over-770-seconds|9c-sampling-step-runs-over-770-seconds]]).
Given a step that runs past 120 s, when 9c samples it, then the build fails naming the step, no table is written,
and the previous table stays published. Given a normal run, the table is the same as before.
Priority: P1. Status: Reviewed. Estimate: S. Sprint: 10. Dependencies: Story E3.
