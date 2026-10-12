---
date_drafted: 2026-10-11
type: user-story
us_id: "US-112"
title: "Keep the edge depth files to the newest 8 runs"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
kind: story
priority: P3
estimate: S
sprint: 13
subsystem: core-output, airflow-pipeline
source_ideas: []
related: ["[[core-output-contract]]", "[[edge-depth-table-format]]", "[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]", "[[decision-log|D-033]]", "[[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]]"]
tags: [user-story]
---

# US-112 Keep the edge depth files to the newest 8 runs

As the owner of the core outputs, I want the edge depth volume to hold the newest 8 runs, the same count as the depth rasters, so that the disk use matches the contract.

The product owner set the count to 8 on 2026-10-12 ([[decision-log|D-033]]).
The count matches `flood_depth_raster_tile`, which keeps the newest 8 runs (`FLOOD_RASTER_KEEP_RUNS`, default 8, in `scripts/flood_extent/raster_load.py`).
The contract page and the edge depth format page still say 3 until this story is `Done`.

On 2026-10-11, the `edge-depth-tables` volume held about 35 `.bin` files.
The contract in [[core-output-contract]] named the newest 3, and the code default in `dags/routing_adapter_dag.py` is 3.
`compose.yml` defaults `EDGE_TABLE_KEEP_RUNS` to 60.
[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] raised it to 100 in the server `.env` for the second replay.
The raised value is the likely cause of the 35 files, but the server's current value is not read, so the cause is unverified.

Work: set the count to 8 in the code default (`dags/routing_adapter_dag.py`), in `compose.yml`, and in the server `.env`.
Set the contract row of the edge depth files to 8 in [[core-output-contract]], and the retention line of [[edge-depth-table-format]] to 8.

Given the count of 8, when task `9c_build_edge_depth_table` publishes on the server after the change, then the volume holds 8 `.bin` files, the file that `latest` names is one of them, and [[core-output-contract]] and [[edge-depth-table-format]] state the same count.

Dependencies: none. The count is the owner's decision ([[decision-log|D-033]]), made on 2026-10-12.

Estimate: S.

## Status history

- **2026-10-11, draft.** Found during the server check of [[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]].
  It was a backlog story with no sprint.
- **2026-10-12, Ready.** The product owner set the count to 8 ([[decision-log|D-033]]). The story named the count the contract named, which was 3, so its title and text now name 8. The contract page changes with this story.
  Sized S (2 points), with no dependency. Picked for Sprint 13.
- **2026-10-12, In progress.** The code default (`dags/routing_adapter_dag.py`) and the `compose.yml` default are 8, with a test for each, and the two pages are updated. The server `.env` change waits for the owner's go.
- **2026-10-12, Reviewed.** Pushed, pulled, and set on the server with the owner's go (details items 3 to 5). It waits for the server screenshot and the owner's acceptance.
- **2026-10-12, Done.** The product owner accepted it after the server screenshot.

## Evidence and details

**Evidence:** the server capture of 2026-10-12 13:12 +07, read only, from `artifacts/docs/stories/evidence/us-112-server-check.sh`.

![[us-112-server-check-output.png|900]]

**Details:**

1. The count is 8 in the code default (`dags/routing_adapter_dag.py`) and in the `compose.yml` default. Two tests cover it: `test_routing_adapter_dag.py` expects `keep=8`, and a new test checks the `compose.yml` default. Both failed on the old code first.
2. [[core-output-contract]] ("Edge depth files") and [[edge-depth-table-format]] ("The `latest` pointer") state 8, with `last_updated` 2026-10-12.
3. Server, with the owner's go: `modular` was pushed and pulled (head `9d4f1e6`). In the server `.env`, `EDGE_TABLE_KEEP_RUNS` went from 100 to 8, with a backup `.env.bak-2026-10-12-us112`. The comparison with the backup showed that line as the only difference.
4. Only the worker was recreated (`docker compose up -d --no-deps airflow-worker`, from the server), because the worker reads `.env` only when it is created and task `9c` runs there. No task was running or queued. The worker is healthy and reports `EDGE_TABLE_KEEP_RUNS=8`. No other service is in `Created` or `Restarting`.
5. No core run is expected without rain, so the retention was applied by hand with the function that `9c` calls: `publish_table` on the current `latest` name with `keep=8`. The volume went from 100 `.bin` files to 8, `latest` still names `20261011T001500.bin` (not moved), and the 8 files are `20261010T211500` to `20261011T001500`. `check_tables.py` reports FRESH (the export, the tables, and the graph agree on hash `8c13d8841f83`), `graphhopper` sees the same 8 files and `latest`, and the backend `/health` is ok.
6. The 92 files removed include the 58 edge depth files of the storm replay. They are kept in the test dataset (`snapshot/edge_depth`, 58 files, checksums verified in [[US-124-save-the-storm-replay-results-and-derived-data|US-124]]). The other 34 were older files of the second replay.
7. Not shown: a real run of `9c` pruning to 8 by itself. The next run reads the same value from the worker environment, and the story records it when it happens.
8. The server screenshot is saved as `us-112-server-check-output.png`. It shows `.env` and the worker at 8, 8 files with `latest` among them, `graphhopper` seeing the same 8 files, FRESH, the two pages at 8, and the 58 storm-replay files in the snapshot.
9. Accepted by the owner on 2026-10-12.
