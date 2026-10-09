---
date: 2026-10-04
type: log
status: active
tags: [log, infra, storage, docker]
related: ["[[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]", "[[2026-10-02-disk-cleanup-and-d-drive-move]]", "[[move-non-ssd-storage-to-d-drive]]"]
---

# C: fills up again, this time with Postgres down

## What happened, in order

1. User reported C: full again. `C:\Users\TECOTEC\AppData\Local\Docker\wsl\disk\docker_data.vhdx`
   held 220.37 GB of the 510 GB used, leaving about 250 MB free. `docker context ls`, `docker
   images`, `docker ps -a`, and `docker system df` all hung. A direct `psycopg2` connection to
   `storage-postgres` on its host port also timed out, so Postgres itself was down, not just the
   Docker CLI.
2. Misread `.claude/CLAUDE.md`'s Docker section and proposed deleting the local Docker Desktop
   data as unused cruft, since the file described a `remote-server` context this machine doesn't
   have. The user corrected this: this session runs directly on the Windows machine the CLAUDE.md
   was written to describe from the Mac's side, so the local engine is this project's real Docker
   host, not unused cruft. A subagent rewrote that CLAUDE.md section to cover both cases (on the
   Mac, or directly on this server) and give a cheap check for which one applies. Full detail in
   [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]], Approach 2.
3. Followed the recovery from [[2026-10-02-disk-cleanup-and-d-drive-move]]: stopped Docker
   Desktop's processes, ran `wsl --shutdown`, and tried to compact the vhdx with `diskpart` while
   it sat offline and unlocked. The compaction failed with "The requested operation requires
   elevation"; this session isn't running as Administrator, the same limit the 2026-10-02 session
   hit. Full detail in [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]], Approach 3.
4. User asked why this filled up again so soon after this week's `docker prune`, and whether it's
   tied to `depth.tif`. Read [[2026-10-02-disk-cleanup-and-d-drive-move]], `scripts/flood_extent/raster_load.py`,
   [[minio-flood-extent-pipeline]], and `artifacts/logs/2026-10-02.md`, and found that the user
   unpaused `flood_mapping_full` on 2026-10-02 at about 15:54 +07 for a 48-hour continuous soak
   test (`US-034`) that runs through today. That's the likely cause, laid out as a hypothesis
   (not yet checked against live numbers) in [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]'s Concerns
   section: 192 insert-then-delete cycles against a large raster column, over two days, can bloat
   `storage-postgres-data`'s on-disk size past what its 8-run retention policy would suggest,
   because Postgres doesn't shrink a table file on `DELETE` until `VACUUM` runs. `docker system
   prune` wouldn't have touched this either way, since it only clears unused images and build
   cache, never a live named volume.
5. User asked to vacuum Postgres immediately. Not possible yet: `VACUUM` needs a live connection,
   and Postgres is the thing that's unreachable. Confirmed again via the same `psycopg2` timeout
   from step 1. Getting the engine to respond again comes first.

## State at the end of this session

- C: free space: about 250 MB, unchanged. Docker Desktop's processes are stopped and WSL is shut
  down, so the vhdx is unlocked, but the `diskpart` compaction that would reclaim space hasn't run.
- `.claude/CLAUDE.md`'s Docker section is rewritten in the working tree, not yet committed.
- Open items, tracked in [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]: the user needs to run `diskpart`
  in an elevated shell; once the stack is back up, whether `flood_depth_raster_tile` is actually
  bloated, and whether the 48-hour soak finished cleanly, both still need checking against real
  numbers.

## Later the same day: the engine comes back, and the real cause

6. The user ran `diskpart /s` in an elevated shell. It compacted the vhdx, but freed almost
   nothing: 220.37 GB to 220.28 GB. Unlike the 2026-10-02 compaction, which recovered 100 GB of
   stale sparse space, this vhdx held mostly live, in-use data. Docker Desktop restarted
   afterward. `docker system df -v` then showed the real breakdown: `storage-postgres-data` at
   85.28 GB, dwarfing every other volume.
7. Queried `storage-postgres` directly. `flood_depth_raster_tile` was 4 GB and held exactly 8
   runs, matching `raster_load.py`'s `DEFAULT_KEEP_RUNS = 8`. It was never the problem; the
   Concerns section this log pointed to in step 4 was wrong. The real weight was `netcdf_values`
   at 56 GB and `flood_extent_polygon` at 13 GB. Reading `scripts/database/netcdf_to_pg.py` and
   `scripts/flood_extent/publish.py` found why: neither table has a retention or pruning step of
   any kind. `prune_step_rows` in `publish.py` prunes `flood_extent_step`, not
   `flood_extent_polygon`. `netcdf_to_pg.py`'s `delete_old_values` only clears a row's own
   `file_id` on re-upload; it does nothing to the file before it. Both tables had been
   accumulating since they were created, back to 2026-09-24, and the 48-hour soak just hit the
   accumulated total hard enough to fill the disk. Full writeup in
   [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]], Approach 4.
8. Paused `flood_mapping_full`. Found and ignored a false alarm: `task_instance` rows for
   `9_build_flood_tiles` and `9b_load_depth_raster` showed `running` from a stale DAG run, but
   `celery inspect active` showed no live task. The worker container had restarted underneath
   them without updating their state.
9. Deleted rows older than 48 hours from both tables, per the user's call to keep only the data
   from the soak test: 176,724,199 rows from `netcdf_values`, 2,121 from `flood_extent_polygon`.
   The delete's own WAL, plus the autovacuum it triggered on `netcdf_values`, then drove C: down
   to 0.02 GB free and Postgres hit `No space left on device` mid-`VACUUM` and crashed. Docker
   Desktop auto-paused the `storage-postgres` container as a result, which likely prevented worse
   damage. The user freed about 34 GB by deleting a 30 GB game install and clearing the npm and
   pip caches, which gave enough room to unpause the container and let autovacuum finish safely.
10. Ran `VACUUM FULL` on `flood_extent_polygon`: 13 GB to 5.1 GB, confirmed by `pg_database_size`
    dropping from 78 GB to 70 GB. Left `netcdf_values` alone. A 1% `TABLESAMPLE` put its live row
    count near 143 million, meaning most of its 56 GB is the soak test data the user wants to
    keep, not dead space; `VACUUM FULL` on it would need 40 to 50 GB of scratch space against the
    34 GB available, which would likely repeat the same crash. The Windows-visible free space
    stayed flat through all of this, 33 to 34 GB, because `VACUUM` reclaims space inside
    Postgres's files but doesn't shrink the vhdx; that still needs another `wsl --shutdown` and
    `diskpart` pass once the cleanup is done.
11. Since every run writes the full mesh again with the same `element_id`, `x`, `y`, `mesh_type`,
    `element_type`, and one of 8 `variable_name` values, and only `timestamp` and `value` change,
    proposed normalizing `netcdf_values` into dimension tables plus a narrow fact table on a
    TimescaleDB hypertable with compression and a retention policy. Written up as
    [[netcdf-values-timescale-migration]], tracked as [[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]]
    (`US-066`, Sprint 5 of `sprint-plan-2`).

## State now

- C: free space: about 34 GB, up from 250 MB, from the user's manual cleanup, not from anything
  this session reclaimed inside Docker.
- `flood_extent_polygon`: fixed, 5.1 GB, holding only live rows.
- `netcdf_values`: still 56 GB. The 48-hour delete removed the pre-soak backlog but left the
  soak's own data in place, by design. `US-066` is the plan to actually shrink its footprint.
- `flood_mapping_full` stays paused until `US-066` lands; unpausing it now would let
  `netcdf_values` and `flood_extent_polygon` start growing again with no retention.
- Still open: the elevated `wsl --shutdown` and `diskpart` pass to convert the Postgres-side
  savings into real Windows free space, and `docker volume prune` for a handful of small orphaned
  volumes (about 460 MB) left over from the 2026-10-02 migration.
