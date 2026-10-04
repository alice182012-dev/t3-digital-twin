---
date_open: 2026-10-04
date_closed:
type: blocker
status: open
severity: P1
subsystem: infra, docker, storage-postgres
approaches_tried: 4
approaches_remaining: 1
tags: [blocker, infra, docker, storage, postgres]
related: ["[[2026-10-02-disk-cleanup-and-d-drive-move]]", "[[move-non-ssd-storage-to-d-drive]]", "[[minio-flood-extent-pipeline]]", "[[2026-10-04-docker-vhdx-disk-full]]", "[[netcdf-values-timescale-migration]]", "[[netcdf-values-storage-redesign]]"]
last_updated: 2026-10-04
---

# Docker's vhdx fills C: again, and Postgres stops answering

## Description

C: dropped to about 250 MB free. `C:\Users\TECOTEC\AppData\Local\Docker\wsl\disk\docker_data.vhdx`
(Docker Desktop's WSL2 virtual disk) held 220.37 GB of the 510 GB used on the drive; nothing else on
the drive was unusual. `docker context ls`, `docker images`, `docker ps -a`, and `docker system df`
all hung with no output. A direct `psycopg2.connect` to `storage-postgres` on its exposed host port
(`127.0.0.1:5433`) timed out too, so the database itself was down, not just the Docker CLI.

This is the same failure as [[2026-10-02-disk-cleanup-and-d-drive-move]], two days after that
session compacted the same vhdx from 172 GB to 69 GB and freed C: to 155 GB.

## Why this matters

Every container on this host is down while the engine can't respond: `storage-postgres`,
`timescaledb`, `minio`, `airflow`, and `graphhopper`. The frontend's live map, routing, and depth
lookups all read from these, so the whole stack is unreachable until the engine comes back and the
containers restart.

## Approaches tried

### Approach 1: inspect the running engine (2026-10-04)

Ran `docker context ls`, `docker images`, `docker ps -a`, and `docker system df -v` against the
local engine to see what was using the space. Every one of these hung and never returned. Confirmed
separately that `storage-postgres` itself was unreachable: a direct `psycopg2.connect(host='127.0.0.1',
port=5433, dbname='minio_custom', user='minio_custom', ...)` against the port `compose.yml` exposes
(`127.0.0.1:${POSTGRES_HOST_PORT:-5432}:5432`, with `.env` setting `POSTGRES_HOST_PORT=5433`) timed
out. Result: the engine, not just the CLI, is stuck, most likely because the host has no free disk
space left for the VM to operate. Not confirmed by any error message; this is a working hypothesis.

### Approach 2: assumed local Docker was unused, asked to wipe it (2026-10-04)

Misread the situation. `.claude/CLAUDE.md`'s Docker section described a `remote-server` context
pointing at `ssh://tecotec@100.67.84.55` and said every `docker` command in this project targets
that remote host. Read on its own, that implied this machine's local Docker Desktop was unused
cruft, so proposed running `wsl --unregister docker-desktop-data` to delete it outright.

The user corrected this: the current session runs directly on the Windows machine at
`100.67.84.55` (hostname `ADMIN`, user `TECOTEC`), which the CLAUDE.md's `remote-server` framing
describes from the opposite end, the Mac's point of view. That file was copied into this repo as is
from the Mac's checkout. `docker context ls` on this machine shows only `default` and
`desktop-linux`, no `remote-server` context at all, which confirms this machine is the Docker host
itself, not a client reaching for one. The 220 GB in `docker_data.vhdx` is this project's real,
live data, not unused cruft. A subagent (report delivered inline, no separate file) rewrote the
CLAUDE.md section into "Docker: check which machine you're on before touching it", covering both
cases and giving a cheap check (`docker context ls`, or `hostname`/IP) to tell which one applies.
That edit is in the working tree, uncommitted, as of this write-up.

### Approach 3: stop Docker Desktop, shut down WSL, compact the vhdx offline (2026-10-04)

Followed the same recovery used in [[2026-10-02-disk-cleanup-and-d-drive-move]]: shut down the VM
and compact the vhdx while it's offline, since this reclaims space Docker already freed internally
without needing a running engine.

1. Ran `wsl --shutdown`. The WSL-specific processes (`wslhost`, `wslrelay`, `vmmemWSL`) exited, but
   several Docker Desktop processes (`com.docker.backend`, `docker`, `docker-agent`,
   `docker-sandbox`) stayed running and still held the vhdx file open.
2. Stopped those with `Stop-Process -Force`. This needed no elevation, since they run under the
   same user account. Free space rose only slightly, to about 4.5 GB, from released VM memory and
   cache, not from reclaiming disk.
3. Ran `diskpart /s <script>` with a script of `select vdisk file=...`, `attach vdisk readonly`,
   `compact vdisk`, `detach vdisk`. This failed: "The requested operation requires elevation." This
   session is not running as Administrator (confirmed with
   `([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(...Administrator)`
   returning `False`), the same limit the 2026-10-02 session hit.

Result: the vhdx is unlocked and ready to compact, but the compaction itself hasn't run. The
diskpart script is saved at a session-scoped scratchpad path that won't exist in a later session;
whoever runs it should copy the three-line script (below) into a new file rather than relying on
that path.

```
select vdisk file="C:\Users\TECOTEC\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
attach vdisk readonly
compact vdisk
detach vdisk
```

### Approach 4: find the real root cause once the engine came back, fix one table by hand, plan the other (2026-10-04)

The user ran the elevated `diskpart` compaction from Approach 3, then Docker Desktop restarted
cleanly. `docker system df -v` showed `storage-postgres-data` itself at 85 GB, not image or build
cache, confirmed by `docker system prune` having already run this week with no effect. Inside
Postgres, the Concerns hypothesis below about `flood_depth_raster_tile` turned out to be wrong:
that table was a healthy 4 GB holding exactly 8 runs, matching `raster_load.py`'s
`DEFAULT_KEEP_RUNS = 8`. The real cause was two other tables with no retention policy at all:
`netcdf_values` (56 GB) and `flood_extent_polygon` (13 GB).

`flood_extent_polygon` turned out to be almost entirely dead TOAST bloat: only 1,463 live rows
behind the 13 GB. A `DELETE ... WHERE valid_time_utc < now() - interval '48 hours'` plus
`VACUUM (FULL)` took it to 5 GB, confirmed safe because the live-row count was tiny. The full
sequence, including a mid-cleanup near-zero-disk scare from the WAL this generated and the
autovacuum it triggered, is in [[2026-10-04-docker-vhdx-disk-full]].

`netcdf_values` is a different shape of problem: the same 48-hour cutoff delete still left about
143 million live rows, because that window is almost the entire 48-hour soak test the user wants
to keep for analysis. There is no quick deletion fix; the table needs a schema redesign before it
can hold a multi-day soak without this recurring. That redesign is planned in
[[netcdf-values-timescale-migration]] (story [[netcdf-values-storage-redesign]], `US-066`,
Sprint 5), not yet implemented.

## Decision and explanation

Partially resolved. `flood_extent_polygon` is fixed. `netcdf_values` needs
[[netcdf-values-timescale-migration]] implemented before this is fully closed; until then, a long
soak test will refill `netcdf_values` the same way. The vhdx itself still needs one more
`wsl --shutdown` + `diskpart compact vdisk` pass to convert the Postgres-side space freed in
Approach 4 into space the Windows host can actually see — the same gap Approach 3 hit, now with
less to compact.

## Concerns

The original hypothesis in this section (`flood_depth_raster_tile` bloat from insert-then-delete
churn without enough autovacuum throughput) did not hold up: that table is healthy. Left here for
the record, since it shaped Approach 1's checks, but do not act on it further.

[[minio-flood-extent-pipeline]]'s stated retention default of 3 for `flood_depth_raster_tile` is
confirmed stale against `raster_load.py`'s actual `DEFAULT_KEEP_RUNS = 8` (also cited by
[[failed-route-shows-previous-mode-route]] as "the backend keeps the newest 8 runs"). Worth fixing
on that concept page separately from this blocker.

## Related topics

- [[2026-10-02-disk-cleanup-and-d-drive-move]]
- [[move-non-ssd-storage-to-d-drive]]
- [[minio-flood-extent-pipeline]]
- [[2026-10-04-docker-vhdx-disk-full]]
- [[netcdf-values-timescale-migration]]
- [[netcdf-values-storage-redesign]]

## Status history

- **2026-10-04, open.** C: at ~250 MB free, local Docker engine unresponsive, Postgres unreachable.
  Diagnosed the vhdx as the cause (Approach 1), corrected an initial misreading that the local
  engine was unused (Approach 2, also fixed in `.claude/CLAUDE.md`), then stopped Docker Desktop's
  processes and shut down WSL to unlock the vhdx for compaction (Approach 3). Compaction itself is
  blocked on needing an elevated shell, which this session doesn't have. Stays `open` until the
  user runs the elevated `diskpart` script, the stack comes back up, and the raster table's actual
  size is checked against the hypothesis above.
- **2026-10-04, open.** Elevated `diskpart` ran and the engine came back up (Approach 4). The
  `flood_depth_raster_tile` hypothesis was wrong; the real cause was `netcdf_values` and
  `flood_extent_polygon` having no retention policy at all. Fixed `flood_extent_polygon` by hand
  (13 GB to 5 GB). `netcdf_values` needs a schema redesign, now planned but not yet built in
  [[netcdf-values-timescale-migration]]. Stays `open` until that plan ships and a final vhdx
  compaction converts the reclaimed Postgres space into Windows-visible free space.
