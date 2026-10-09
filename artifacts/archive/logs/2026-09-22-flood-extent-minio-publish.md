---
date: 2026-09-22
type: log
branch: calculate-depth-cli-subprocess
status: done
tags: [minio, flood-extent, calculate-depth, frontend, docker]
related: ["[[flood-extent-polygon-tiles-airflow-minio]]", "[[calculate-depth-threedidepth-cli]]", "[[minio-flood-extent-pipeline]]"]
---

# Flood-extent tiles move to MinIO

Date: September 22, 2026. Commits: `9c0942a` (calculate_depth CLI rewrite),
`a10c1be` (MinIO publish pipeline). Branch `calculate-depth-cli-subprocess`,
merged into `main` and pushed to `alice182012-dev/t3-digital-twin`.

## Context

The flood-extent tile pipeline (`scripts/flood_extent/flood_extent.py`)
built vector tiles on local disk and served them from a bind mount into the
frontend container. That only works when the Airflow worker and the
frontend share a filesystem. In production they run on separate hosts, so
the bind mount can never deliver a tile to the frontend. This session
replaced local-disk serving with MinIO, and fixed a related gap where a
published run's timesteps weren't reachable by the map's automatic
timestep picker.

## calculate_depth's CLI-subprocess rewrite

Commit `9c0942a`, landed before this session's main work. `calculate_depth.py`
called `threedidepth.calculate_waterdepth()` in-process. It now shells out
to the `threedidepth` console script per timestep, matching every other
step in the pipeline (GRASS, `gdal_polygonize.py`, `ogr2ogr`), which already
invoke CLI tools instead of library functions.

Validation: a new manual test DAG (`dags/calculate_depth_manual_test_dag.py`)
triggers a real 3Di simulation and runs `calculate_depth` on the result, in
isolation from the production DAG. A pixel-equivalence check against a
fresh run of the old in-process code, on the same fixtures, confirmed the
output was identical (`np.array_equal`). `calculate_depth.py` is flagged
fragile in this codebase's history, so this change went through the manual
test DAG first rather than editing the production DAG directly.

## The MinIO publish pipeline

### `publish.py` replaces the local-disk publish path

`scripts/flood_extent/publish.py` is new. `publish_run` builds each
timestep's tiles with `flood_extent.py`'s existing `Pipeline`, uploads them
to a MinIO bucket, and writes one row per dissolved band polygon to a new
`flood_extent_polygon` PostGIS table (`scripts/database/create_flood_extent_tables.py`).
Uploads run in a thread pool. The PostGIS writes run sequentially after,
because a `psycopg2` connection isn't safe to share across threads. Bucket
pruning and a 24-hour local cleanup (`output_depths/` and the publish work
directory) only run once every timestep in the run has succeeded, so a
partial failure can't prune a still-good older run.

`flood_extent.py`'s `build_run_tiles` and `prune_runs` are gone. They wrote
tiles straight to a local `tiles_root` and had exactly one caller,
`flood_mapping_dag.py`'s task 9. `publish_run` replaced that caller, so the
old functions had no remaining callers and no reason to stay.

Both DAGs now call `publish_run`: `dags/flood_mapping_dag.py`'s task 9
(production), and two new tasks in
`dags/flood_forecast_state_test_dag.py` (`3b_build_tiles_event1`,
`6b_build_tiles_event2`, for manual end-to-end testing after each
simulated event's depth calculation).

### Local bind mount to MinIO proxy

`floodmap/graphhopper-maps/nginx.conf`'s `/flood-extent/` location used to
serve files straight from a bind-mounted folder. It now proxies to MinIO,
following the same `resolver`/`set $backend_host` pattern the file already
used for `/api/gh/`. The tile URL path didn't change
(`/flood-extent/<run>/<timestep>/{z}/{x}/{y}.pbf`), so the frontend code
that builds that URL (`floodExtentTiles.ts`, `FloodExtentLayer.tsx`) needed
no changes. `compose.yml` gained a `flood-extent` bucket in `minio-init`,
set to anonymous download. It's the only public bucket, since it's the
only one nginx proxies straight to the browser. The MinIO API port itself
stays bound to `127.0.0.1`.

Whether to build this MinIO path at all was a real decision, not an
assumption: the plan going into this session took the tile pipeline's
existing local-disk output as one available option and MinIO as another.
Asking directly whether the worker and the frontend run on the same host
in production settled it. They don't, so the bind mount was never going
to work there, and MinIO wasn't optional.

### Timestep discovery: reusing FloodStore instead of a second manifest

A prior plan (`artifacts/archive/plans/flood-extent-polygon-tiles-airflow-minio.md`)
called for a `latest.json` manifest and a `pickExtentStep` function to find
the timestep closest to now. Reading `floodmap/graphhopper-maps/src/floodmap/FloodStore.ts`
before building that found it already does this: `findNearestTimestepIndex`
and a 45-minute `FRESH_DATA_WINDOW_MS` cutoff, driving `FloodExtentLayer.tsx`'s
selected timestep today. Building a second, parallel manifest system would
have duplicated a working mechanism instead of reusing it.

What FloodStore's timesteps list didn't do was let the map discover
flood-extent runs at all. `GET /flood/timesteps` read `flood_road_values`,
populated by the routing pipeline's road-mapping chain, which has no
connection to the tile-publish pipeline. A run published by `publish_run`
was invisible to the map's automatic picker. The only way to view it was
`floodExtentTiles.ts`'s `?flood_extent=<run>/<timestep>` URL override,
built for exactly this kind of manual check.

`floodmap/graphhopper-flood-road/backend/flood_extent_runs.py` closes that
gap. It wasn't written in this session. It showed up as uncommitted work
in the tree partway through, alongside edits to `flood_areas.py`,
`server.py`, and `README.md`. Before including it in the commit, it got the
same scrutiny as anything else going in: read in full, and run directly
against the live `flood_extent_polygon` table (not just its own test
fixtures) to confirm `list_runs`, `latest_run`, and `list_timesteps` return
correct data, including the Vietnam-local time conversion matching
`publish.py`'s `valid_time_utc`. `server.py` now imports `list_runs` and
`list_timesteps` from `flood_extent_runs.py` instead of `flood_areas.py`.
Routing (`POST /route`, `derive_areas`) still reads `flood_road_values`,
unchanged. Only the map's timestep picker moved. The old
`test_flood_areas.py`, which tested the two functions that moved, was
deleted in favor of the new `test_flood_extent_runs.py`.

### Legend colors from the reference QML

`floodmap/graphhopper-maps/src/floodmap/depthScale.ts`'s band colors used
to be a hand-picked palette. The plan called for sampling the reference
QML's (`test/waterdepth_steps/waterdepth_steps/depth_20251006_000000.qml`)
interpolated ramp at the display bands' depth thresholds. Doing that
literally doesn't work: the QML's value axis spans 0 to about 4.3 meters,
the actual maximum depth in that one scene, while the display bands only
cover 0.05 to 0.6-plus meters. Sampling at those meter values lands in the
ramp's first 14%, so six of the seven bands come out as nearly identical
pale blues, with the seventh jumping straight to near black.

Both the literal sampling and an alternative were computed and shown side
by side: map the seven display bands onto the ramp's nine stops by rank
instead of by value, reusing the QML's actual ColorBrewer-Blues sequence
in order. The user picked rank order. `depthScale.ts` now uses it
(`#deebf7` through `#08306b`), and the stale comment referencing the
deleted `backend/tiles.py` is gone.

### Periodic frontend refresh

`floodmap/graphhopper-maps/src/floodmap/useFloodState.ts`'s
`useFloodBootstrap` called `loadFloodTimesteps()` once, on mount, with
nothing to refetch it later. A session left open would never see a run
published after page load. It now refetches every five minutes
(`TIMESTEP_REFRESH_INTERVAL_MS` in `FloodStore.ts`), well inside the
45-minute freshness window. `reanchorTimestepIndex`'s existing behavior
(follow the current selection if it's still in the new list, instead of
always jumping to nearest-to-now) is untouched. That's a deliberate
choice to not move the map out from under someone mid-inspection, not
something this change should override.

## Verification

Real artifacts, not proxies, at each step:

- `Pipeline.check()`'s new polygon capture (`flood_extent.py`), against a
  real depth raster: valid geometries, correct Hanoi-area coordinates.
- `publish_run`, against the real `storage-postgres` and a scratch MinIO
  bucket: correct S3 keys, correct upserted rows, correct areas and
  geometry types.
- `flood_mapping_dag.py`'s actual task function, not `publish.py` in
  isolation, invoked through a mock `TaskInstance` against real fixture
  data, to catch bugs in the DAG glue itself.
- The nginx proxy, end to end: a real published tile through the rebuilt
  `flood-routing-frontend` returned 200 with the right content type. A
  missing one returned 404, not the single-page app's `index.html`.
- Frontend rendering, via gstack `browse`: a published run rendered on the
  map. The first look, a zoomed-out screenshot, appeared empty: a false
  negative. A pixel diff between Map mode and Flood mode found roughly
  85,000 differing pixels, several shifted distinctly toward blue. A
  closer zoom showed the pale fill clearly over a park and a school
  compound. The tiles were rendering correctly the whole time. The lighter
  bands are just subtle against the OpenStreetMap basemap at low zoom and
  0.75 fill opacity.
- `tsc --noEmit` and the full Jest suite (177 tests, 17 suites) for every
  frontend change, run in the `gh-maps-dev` container.
- `python3 -m unittest` for `scripts/flood_extent/test_publish.py` (new:
  `valid_time_utc`'s UTC+7 conversion, `cleanup_old_files`'s age logic).

## Two unrelated incidents

**Docker Desktop's engine wedged.** `docker info` and `docker ps` returned
`500` errors mid-session, unrelated to any config change. A plain
quit-and-relaunch didn't fix it: Docker Desktop's own backend log
(`%LOCALAPPDATA%\Docker\log\host\com.docker.backend.exe.log`) showed
`still waiting for init control API to respond`, minutes past when it
should have started, with `/run/guest-services/socketforwarder-receive-fds.sock`
never appearing. The Linux VM's guest-side init never came up. That isn't
a slow boot. `wsl --shutdown`, then relaunching Docker Desktop, cleared it.
All 15 containers came back via their `restart: unless-stopped` policies.

**The real OSM extract arrived.** `hanoi-model-area.osm.pbf` became
available at `data/mapping/inputs/hanoi-model-area.osm.pbf`. `compose.yml`
expects it at `../grasshopper-routing/osm/hanoi-model-area.osm.pbf`, one
directory up from the repository. That path already existed, but as an
empty directory Docker had auto-created when the file was missing. That
directory was the actual cause of an earlier mount error ("not a directory"). Removing the
stray directory, copying the real file into place, deleting the now
unneeded `compose.override.yml` stopgap, and clearing the
`graphhopper-graph-cache` volume let GraphHopper rebuild from the real
extract: 51,328 nodes, 67,833 edges, all three vehicle profiles.

## Open

- `flood_mapping_full`, the production DAG, is paused. Unpausing it is the
  user's call, not done in this session.
- No real Airflow-scheduled run of either DAG happened this session. Both
  trigger billed 3Di simulations, so that stayed the user's call throughout,
  matching the calculate_depth work before it.
- Every test artifact from this session (MinIO test runs, `flood_extent_polygon`
  test rows, `data/output_depths_cli_test`, `data/mapping_state_test`,
  `data/results_cli_test`, `data/mapping/flood_extent_work`) was deleted
  before the final commit. Nothing test-related is left in the bucket, the
  table, or the filesystem.

## See also

- `artifacts/archive/plans/calculate-depth-threedidepth-cli.md`: the
  step-by-step plan and progress log this work followed.
- `artifacts/archive/plans/flood-extent-polygon-tiles-airflow-minio.md`:
  the earlier plan this session's MinIO design updates and supersedes in
  part (see that file's own status section).
- `artifacts/SW Architecture.md` #8: why routing and map-display
  visualization read different flood tables.
