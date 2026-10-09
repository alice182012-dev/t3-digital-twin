---
date: 2026-10-02
type: plan
branch: front-end-according-to-mock-up
status: resolved
tags: [plan, infra, storage, docker]
related: ["[[2026-10-02-disk-cleanup-and-d-drive-move]]"]
---

# Plan: move non-SSD-sensitive pipeline storage to D:

## Context

C: is an NVMe SSD (PNY CS1031, disk 1). D: is a SATA spinning HDD (WDC WD10EZEX, disk
0, 587 GB free). Earlier the same day we freed C: space by pruning unused Docker images
and build cache (~16 GB) and compacting `docker_data.vhdx` (172 GB to 69 GB), bringing C:
free space to ~155 GB. The user now wants anything in this repo's Docker/pipeline storage
that doesn't need SSD latency moved to D:, to keep C: headroom for the long run instead of
refilling it.

## What's on disk, and why each one does or doesn't move

`compose.yml` has two kinds of storage: host bind mounts (plain files on C:, outside the
Docker vhdx) and named volumes (managed by Docker, physically inside `docker_data.vhdx`,
also on C: today).

Bind mounts, from the `x-airflow-common` block (compose.yml:52-62):

- `./dags`, `./config`, `./plugins`, `./scripts` — small, and `./dags`/`./scripts` are
  re-read every DAG-processor scan cycle (default 30s). HDD seek latency on frequent small
  reads would show up as scheduler lag. Stay on C:.
- `./data` — 682 MB `data/mapping` (batch pipeline working/output dirs, written and read
  on a 15-minute run cadence, already has a 24h cleanup policy in `flood_mapping_dag.py`),
  plus `data/inputs` (103 MB, read once per run) and `data/mapping_state_test` (14 MB, test
  fixtures). This is sequential, batch-cadence I/O, not latency-sensitive the way a DB or a
  live routing query is. Moves to D:.
- `./floodmap/graphhopper-flood-road/scripts` (read-only) and the GraphHopper per-profile
  config YAMLs — trivially small, mounted read-only. Not worth relocating.

Named volumes (compose.yml:420-426):

- `graphhopper-graph-cache` — read on every live routing query. Stays on C:.
- `airflow-postgres-data` — Airflow's own scheduler/metadata DB. Stays on C:.
- `storage-postgres-data`, `timescaledb-data` — serve the frontend's depth/map lookups and
  flood metrics; both are queried interactively. Stay on C:.
- `minio-data` — serves published flood-extent tiles straight to the browser map. Latency
  shows up as map tile load time. Stays on C:.
- `airflow-logs` — task log files, written once per task run and read only when someone
  opens a log in the Airflow UI. Not latency-sensitive. Moves to D:, via a `local` driver
  bind (`driver_opts: {type: none, o: bind, device: ...}`) so the service definition that
  references `airflow-logs:/opt/airflow/logs` doesn't change, only the volume's backing
  path.

So two things move: the `./data` bind mount, and the `airflow-logs` named volume.
Everything DB- or routing-latency-sensitive stays on C:'s SSD, matching the constraint the
user raised earlier in this session (D: being an HDD rules out moving Postgres/
TimescaleDB/MinIO/GraphHopper's cache).

## Implementation

1. Create `D:\airflow_new_data\data` and `D:\airflow_new_data\airflow-logs`.
2. Stop the stack (`docker compose down`, volumes kept).
3. Move `data/` (repo root) to `D:\airflow_new_data\data`, then point `compose.yml`'s
   `./data` bind mount at an env-overridable host path (`${DATA_HOST_PATH:-./data}`) set to
   the D: path in `.env`, documented with a default comment in `.env.example`. Using an env
   var instead of a silent NTFS junction keeps the real location visible to anyone reading
   `compose.yml`/`.env.example`, consistent with how every other host-specific path in this
   repo is already handled.
4. Copy the existing `airflow-logs` volume's contents to `D:\airflow_new_data\airflow-logs`
   (via a throwaway container bind-mounting both the old named volume and the new host
   path), then redefine `airflow-logs` in `compose.yml` with `driver: local` /
   `driver_opts` pointing at that path.
5. `docker compose up -d`, confirm all services report healthy.
6. Verify: inspect the running containers' mount source for `/opt/airflow/data` and
   `/opt/airflow/logs` to confirm they resolve to D:, confirm a task log file is readable
   from the Airflow UI, and confirm `data/mapping` still gets written on the next scheduled
   run.

## Rollback

Both changes are reversible by moving the directories back to C: and reverting the
`compose.yml`/`.env` changes; nothing here deletes data, only relocates it.

## What actually shipped

Steps 1-6 ran as planned, with one unplanned fix along the way: bringing the stack back up
surfaced that `minio-init`'s image (`quay.io/minio/mc`) can no longer be pulled from
anywhere official (MinIO archived the open-source `mc` project; see the day's log,
[[2026-10-02-disk-cleanup-and-d-drive-move]], for the full finding). Fixed by switching
`minio-init` to `alpine:latest` and fetching the `mc` binary from its GitHub release asset
instead, checksum-verified. Confirmed via `docker exec` + a host-side file check that both
the `./data` bind mount and the recreated `airflow-logs` volume resolve to
`D:\airflow_new_data\`. All compose services report healthy.
