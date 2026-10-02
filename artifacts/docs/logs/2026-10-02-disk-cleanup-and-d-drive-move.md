---
date: 2026-10-02
type: log
status: resolved
tags: [log, infra, storage, docker]
related: ["[[move-non-ssd-storage-to-d-drive]]"]
---

# Disk cleanup, Docker vhdx compaction, and moving pipeline storage to D:

C: (NVMe SSD) was down to 35.4 GB free. D: (SATA HDD, 587 GB free) was unused.

## What happened, in order

1. Confirmed `com.docker.service` was stopped, which was causing `docker info` to 500 and
   Docker Desktop to report a resource error. User restarted it (needed admin rights this
   session doesn't have).
2. Cleaned up this repo's own stale local storage: deleted
   `floodmap/graphhopper-maps/node_modules` (236 MB, rebuildable), an orphaned
   `data/flood-extent/` directory (74 MB, not referenced by any code or compose mount,
   stale since 2026-09-21), and ran `git gc` to clear leftover `tmp_pack_*` garbage from an
   interrupted repack. `data/mapping/results` (570 MB) was checked and left alone — it
   already has a 24h cleanup policy in `flood_mapping_dag.py`.
3. Found the real cause of C: filling up: `docker_data.vhdx` (Docker Desktop's WSL2 virtual
   disk) was 172 GB, of which `docker system df` showed only ~89 GB was actual data. Ran
   `docker system prune -f`, `docker image prune -a -f`, `docker builder prune -a -f`
   (freed ~16 GB immediately, since the vhdx is a sparse file). Then compacted the vhdx via
   `wsl --shutdown` + `diskpart` (`attach vdisk readonly` / `compact vdisk`), which needed
   killing lingering `Docker Desktop`/`com.docker.backend`/`vmmemWSL` processes first since
   `attach` failed with the file still in use. Result: vhdx 172 GB to 69 GB, C: free space
   35.4 GB to 155 GB. All 15 containers came back up afterward with volumes intact.
4. User asked to move anything not needing SSD speed to D:. Confirmed C: is NVMe (disk 1,
   PNY CS1031) and D: is a spinning SATA HDD (disk 0, WDC WD10EZEX) via
   `Get-PhysicalDisk`/`Get-Partition`, which ruled out moving Postgres/TimescaleDB/MinIO/
   GraphHopper's cache (all latency-sensitive) and narrowed the move to the `./data` bind
   mount and the `airflow-logs` named volume. Full reasoning and the exact diff in
   [[move-non-ssd-storage-to-d-drive]].
5. While bringing the stack back up with the new mounts, found `quay.io/minio/mc` and
   `docker.io/minio/mc` both deny anonymous pulls now, and `dl.min.io`'s `mc` binary
   download returns `410 Gone`: MinIO archived the open-source `mc`/server/KES projects and
   pulled them from every official distribution channel. This wasn't caused by the move or
   the earlier prune; it would have hit this project on any fresh pull of that image from
   here on. Fixed `minio-init` in `compose.yml` to fetch the `mc` binary from the matching
   GitHub release asset instead (verified against MinIO's own published sha256sum), since
   GitHub doesn't retroactively delete release assets.
6. Verified the `airflow-logs` named volume needed removing and recreating for its new
   `driver_opts` bind to take effect — Docker doesn't reconfigure an existing volume just
   because `compose.yml` changed. Confirmed both mounts land on D: by writing a test file
   into the running `airflow-worker` container and checking it appeared directly at
   `D:\airflow_new_data\...` on the host.

## State after this session

- C: free space: 35.4 GB to 155 GB.
- `./data` bind mount and `airflow-logs` volume: both on `D:\airflow_new_data\`.
- Postgres, TimescaleDB, MinIO, GraphHopper's graph cache: unchanged, still on C:'s SSD.
- All 18 compose services healthy.
