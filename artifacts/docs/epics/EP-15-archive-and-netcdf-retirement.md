---
date_drafted: 2026-10-08
type: user-story
us_ids: ["US-094", "US-095"]
status: draft
subsystem: core-output
source_ideas: []
related: ["[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[decision-log]]", "[[EP-12-core-output-hygiene|core-output-hygiene-stories]]", "[[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]]", "[[3di-simulation-orchestration]]", "[[archive-3di-results-and-retire-netcdf-values]]", "[[move-non-ssd-storage-to-d-drive]]", "[[2026-10-08]]"]
tags: [user-story, epic, archive, netcdf, retention, sprint-10, sprint-11]
---

# Epic: archive the 3Di results and retire the netcdf_values ingest

Two decisions of 2026-10-08 (D-016 and D-018 in [[decision-log]]) become two stories. The first keeps each real-rain
run's `results_3di.nc` on the server's D: drive. The second removes the `netcdf_values` ingest, which holds 2,428 MB
on the server and costs about 81 s per run. Story 2 reads the archive that Story 1 proves, so Story 1 comes first.
Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic shape in
[[user-story-types]]. A story reaches `Done` only with evidence and numbered details, recorded here and in
[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. The plan is [[archive-3di-results-and-retire-netcdf-values]].

Concept pages and the architecture doc are not edited now. They change when the stories are built: [[3di-simulation-orchestration]],
[[architecture-block-diagram]], [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]] if it describes the ingest, and the US-066 pages.

- [[US-094-archive-results-3di-nc-and-a-run|US-094]] Archive `results_3di.nc` and a run record to D: when the pipeline reads real rain. Story 1.
- [[US-095-retire-the-netcdf-values-ingest|US-095]] Retire the `netcdf_values` ingest. Story 2.

## Open questions for the user

1. ~~Is `D:\airflow_new_data\archive` the right folder?~~ Confirmed by the user on 2026-10-08.
2. ~~Do `netcdf_files` and `netcdf_variables` on `storage-postgres` go with the retirement, or stay?~~ They go (the user, 2026-10-08).
3. After retirement, the `timescaledb` container holds only three empty tables. Retire the container too? This is a
   separate decision and nothing here decides it.
4. ~~What proves `US-094` if no real rain falls?~~ A one-off run with real rain counts as the proof (the user, 2026-10-08). The rain gate skips a run when the Tomorrow.io forecast is below `FLOOD_RAIN_THRESHOLD_MM_HR`, so the one-off run needs a forecast above the gate or a way to run one real-forecast simulation despite it. The user chose on 2026-10-08 to wait for a real forecast above the gate (option 1): no gate change and no override. So the proof waits for weather, and `US-095` and `US-086` wait with it.

## Status history

- **2026-10-08, draft.** Written at the user's request after decisions D-016 and D-018. The next free ID was `US-094`.
- **2026-10-08, draft.** `US-094` is in Sprint 10, the earliest sprint that satisfies the dependency of `US-095`
  (Sprint 11, the user's choice). This is a decision made by dependency under rule 3, and the user can override it.
- **2026-10-08, draft.** The user asked for a free-space check in `US-094` and for `netcdf_files` and `netcdf_variables` to be dropped in `US-095`. Open question 4 (what proves `US-094` without real rain) is still unanswered.
- **2026-10-08, draft.** The user decided a one-off real-rain run counts as the proof of `US-094`, so `US-095` does not wait for a storm. The one-off run must get past the rain gate, which is unsettled.
- **2026-10-08, draft.** The user chose option 1 for the rain gate: the proof of `US-094` waits for a real forecast above the gate. No gate change and no override. `US-095` and `US-086` wait for it.
