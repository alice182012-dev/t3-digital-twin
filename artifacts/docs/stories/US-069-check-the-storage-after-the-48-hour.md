---
date_drafted: 2026-09-29
type: user-story
us_id: "US-069"
story_label: "12"
epic: "[[EP-07-carried-over-backlog]]"
status: Not started
priority: P1
estimate: S
sprint: 8
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
---

# US-069 Check the storage after the 48-hour replay to see if the retention fixes work

As the pipeline owner, I want the storage numbers of the server read at the start, the middle, and the end of the 48-hour replay, so I know whether `US-066` and `US-067` stop the growth that filled C: on 2026-10-04.
Given the replay of `US-063` running on the server for 48 hours, when the numbers are read at the start, at 24 hours, and at 48 hours, then each reading holds the free space on C:, the size of `docker_data.vhdx`, the size of the `storage-postgres-data` volume, the size of `minio_custom`, the size of the `netcdf_values` hypertable (compressed and not), and the size and row count of `flood_extent_polygon`. The check passes if the sizes of the three database objects stop growing between the 24-hour and the 48-hour reading, `flood_extent_polygon` holds rows for no more than the newest `keep_runs` runs, and no container was auto-paused for lack of space.
Priority: P1. Status: Not started. Estimate: S. Sprint: 8 ([[SP-02-routing-engine-foundations|sprint-plan-2]], moved from Sprint 5 on 2026-10-05). Dependencies: the DAG unpaused for 48 hours, and the replay of Story 8 (`US-063`) running, and the user's read-only access to the server. The replay's start time is still to be given. The 24-hour and 48-hour readings follow from it.
Proposed pass mark, not yet confirmed by the user: growth of 10 percent or less in each of the three database objects between hour 24 and hour 48. The starting values are the ones in [[2026-10-05]] (C: 163.4 GB free, `storage-postgres-data` 16.01 GB, `minio_custom` 14 GB, `flood_extent_polygon` 5.1 GB).
The readings are read-only. The same run is the retest for `US-034` and `US-037`, so this story adds no load.
Revised acceptance (2026-10-08, D-015). The check runs on the 12-hour replay of `US-088`, not the 48-hour one. Read the same numbers at the start (about 15:05 +07 on 2026-10-08), at hour 6 (about 21:05 +07), and at hour 12 (after the last simulating run at 03:00 +07 on 2026-10-09). The check passes if the three database objects stop growing between hour 6 and hour 12, `flood_extent_polygon` holds rows for no more than the newest `keep_runs` runs, and no container was auto-paused for lack of space. The start reading is partial (15:17 +07: C: free, `docker_data.vhdx`, `minio_custom`, `flood_extent_polygon` only). The pass mark is growth of 10 percent or less per database object between hour 6 and hour 12.
