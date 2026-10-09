---
date_drafted: 2026-09-29
type: user-story
us_id: "US-042"
story_label: "E4"
epic: "[[EP-08-edge-depth-table]]"
status: Done
priority: P0
estimate: S
sprint: 7
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
---

# US-042 Publish the table atomically and keep the newest three runs

As a reader, I want a new table to appear in one step, so I never read a half-written file.
Given a reader that polls in a loop, when the task publishes a table, then the reader sees the old table or
the new one and never a partial file. Given four runs, when the fourth publishes, then the oldest is
removed. A failed task leaves the previous `latest` in place and does not block the DAG.
The story also picks the storage, a volume or MinIO, and records why.
Priority: P0. Status: Done. Estimate: S. Sprint: 7. Dependencies: Story E3 (done).
Storage decision: the Docker named volume `edge-depth-tables`, not MinIO and not a folder under `DATA_HOST_PATH`. The reasons are in [[edge-depth-table-publish]], decision 1.
Evidence: ![[us-042-atomic-publish-server-output.png|700]]
Details:
1. What: the publish step of the edge depth table. `latest` moves to a new table in one step, only forward, and the newest 3 tables stay. The tables live on a new Docker volume, `edge-depth-tables`, which the Airflow worker writes and the routing readers will mount read-only. Task 9c now builds and then publishes.
2. How: tests first. A reader thread read an empty pointer from the old `write_latest` (a write in place), so it now writes a temporary file and renames it over `latest`. `publish_edge_depth.py` reads the table back whole (a bad file is removed and `latest` stays), moves the pointer only forward under a lock on the folder, keeps the newest 3 plus the pointer's table, and removes temporary files older than an hour. 83 tests in `scripts/edge_depth/`, 18 in the DAG graph test. Three changes made tests fail: no lock, a pointer that can move back, and retention that can remove the pointer's table. On the server `publish_check.py` published 41 tables of the real size while a reader in its own process polled.
3. Why: a reader must never see a half-written table or an empty pointer, and the disk must not fill with old tables. The storage is a named volume because the readers then do not depend on Windows file sharing for the rename of `latest`. MinIO would put an S3 client and credentials into the routing readers for three files of 1 MB.
4. Effect: on the server, 11,878 reads in the other process, none failed, and the reader saw all 41 pointer moves. When the last publish ended, `latest` named the newest table and 3 tables were left. The real `latest` (`20261005T120000.bin`) was not touched, because the check works in a scratch folder on the same volume. `US-043` can read `latest` and the tables from the volume, and `US-044` can build its stale-table check on the graph hash in the header.
5. Limits: the reader of the check runs in the same container as the writer, as a separate process, and not in a second container. A second container shares the same volume and the same Linux kernel, so the rename semantics are the same, but the Java reader of `US-043` is the first real cross-container reader. Task 9c was not run in a real DAG run, because the DAG is paused. The old build output in `data/mapping/edge_depth` on the D: drive is not read and can be deleted. The evidence image is rendered from output the user pasted.
