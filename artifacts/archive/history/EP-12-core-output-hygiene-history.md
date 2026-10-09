---
date: 2026-10-10
type: archive
status: archived
tags: [archive, history]
related: ["[[EP-12-core-output-hygiene]]"]
---

# EP-12-core-output-hygiene: archived story-level history

Lines moved out of the Status history of [[EP-12-core-output-hygiene]] on 2026-10-10 under the rule "Write each fact once". Each fact is also in its story file. Not read in normal sessions.

- **2026-10-08, draft.** Story 1 (`US-086`) prunes rows older than 24 hours instead of keeping N runs (D-017). The user decided this, after the raw 3Di output archive was chosen (D-016).
- **2026-10-08, draft.** Story 1 (`US-086`) depends on `US-094` (archive `results_3di.nc` to D:, Sprint 10 in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]), because the 24-hour prune is safe only if the archive works (D-017). See [[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]].
- **2026-10-09, active.** `US-087` is `Done` (`be45e01`, test passes on the server PostGIS in a throwaway database). The workflow ran on GitHub Actions and passed (run 37869621614).
- **2026-10-09, active.** `US-086` is `Reviewed`: built and merged, the first prune ran (368 runs and 13,749,316 rows deleted, 45 runs kept), evidence `us-086-prune-check-output.png`. It reaches `Done` after the task runs once inside Airflow.
