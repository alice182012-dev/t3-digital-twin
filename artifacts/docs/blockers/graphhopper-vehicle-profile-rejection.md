---
date_open: 2026-09-14
date_closed: 2026-09-23
type: blocker
status: resolved
severity: P2
subsystem: graphhopper
approaches_tried: 5
approaches_remaining: 0
tags: [blocker, graphhopper]
related: ["[[graphhopper-backend]]", "[[2026-09-14]]"]
last_updated: 2026-09-23
---

# GraphHopper pinned image rejects any new vehicle profile

## Description

The `israelhikingmap/graphhopper` image pinned in `compose.yml` (digest
`sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`, a 12.0-SNAPSHOT dated
2026-06-18) fails at startup with `Cannot compile expression: '<name>_access' not available` for
any vehicle encoded value beyond the three already baked into the current working graph
(`car_access`, `hgv`, and friends). The failure happens in
`GraphHopper.checkProfilesConsistency()` before any OSM import runs (confirmed via logs: no
import progress lines, `graph-cache` volume stays empty), so it isn't a stale-cache or
config-syntax issue.

## Why this matters

Blocks adding a `foot` profile (pedestrians blocked at 40 cm depth, per the user's requirement)
and any other new vehicle profile, such as exposing `truck` in the frontend. The backend side of
the `foot` profile is already done and inert: `scripts/flood_utils.py`'s
`VEHICLE_PROFILES["foot"]` (threshold 40 cm) needs no further backend change once a `foot`
GraphHopper profile actually exists. `foot_custom.json` and `foot_avoid_private_node_custom.json`
in `floodmap/graphhopper-flood-road/graphhopper/` are ready and untested against a fixed build.

## Approaches tried

### Approach 1: GraphHopper's own bundled foot.json, verbatim

Copied GraphHopper's bundled `foot.json` in unmodified. Failed the same way: rejected at startup
before any OSM import.

### Approach 2: Trimmed foot.json

Dropped `hike_rating` and `mtb_rating`, which need encoded values this OSM extract has no use for
(same precedent as `truck_custom.json` dropping `turn_costs`). Same failure.

### Approach 3: Dropped foot_priority specifically

Narrowed further, removing `foot_priority` on its own. Same failure.

### Approach 4: Synthetic bike_test profile (isolation test)

Built a from-scratch `bike_test` profile referencing only `bike_access`, with zero dependency on
`foot` at all, to confirm this isn't pedestrian-specific. Failed identically, confirming the
pinned build rejects any newly declared vehicle encoded value, not something particular to `foot`.

A raw `docker run` of the same image (bypassing `docker compose`) hung at ~100% CPU with no import
progress for several minutes on two separate attempts, for reasons unrelated to this bug; see
Concerns below.

### Approach 5: read the entrypoint script instead of the config (root cause)

The prior four approaches all diagnosed from the Java-side error and config.yml. The actual cause
was in `graphhopper.sh`, the image's entrypoint script:

```bash
: "${GRAPH:=/data/default-gh}"
...
exec "$JAVA" $JAVA_OPTS ... -Ddw.graphhopper.graph.location="$GRAPH" $GH_WEB_OPTS -jar "$JAR" $ACTION $CONFIG
```

`GRAPH` only changes if the container command passes `-o <dir>` / `--graph-cache <dir>`.
`compose.yml`'s `entrypoint: ["./graphhopper.sh", "-c", "config.yml"]` never did, so every start
injected `-Ddw.graphhopper.graph.location=/data/default-gh` as a JVM system property, and Dropwizard
system-property overrides win over the YAML file. `config.yml`'s own `graph.location:
/data/graph-cache` was silently ignored on every single start.

Confirmed directly on the running container: `docker exec ... cat /graphhopper/config.yml` showed
the real, correct config, but the startup log said `loaded graph at:/data/default-gh` anyway.
`/data/graph-cache`, the actual mounted named volume declared in `compose.yml`, was empty (just `.`
and `..`) — genuinely never used, which is why every earlier attempt saw the cache stay empty and
took that as evidence the failure predated import. `/data/default-gh`, not declared in `compose.yml`
at all, held a real, fully-imported graph matching the Hanoi bounding box, with files dated hours
before the container was even recreated: it survives `--force-recreate` because it's baked into the
image's own layers, not the container's writable layer. That graph's `EncodingManager` only knew
`car_access`, `hgv`, and the other built-in-profile values, frozen at whatever point this pinned
digest was originally built. No config change could ever add a new encoded value to it, because no
import ever ran on this deployment, for any of the four earlier attempts.

## Decision and explanation

Resolved 2026-09-23. Fix: add `-o /data/graph-cache` to the `graphhopper` service's `entrypoint` in
`compose.yml`, so the app imports the mounted OSM extract into the real, persistent volume instead
of loading the image's frozen `/data/default-gh` graph. Verified live on the remote host
(`100.67.84.55`, `airflow_new` compose project):

1. Applied the entrypoint change alone (config.yml still car/motorbike/truck only) and
   force-recreated; no volume wipe needed yet, `graph-cache` already started empty. Logs showed
   `start creating graph from /data/hanoi-model-area.osm.pbf` (a real import, ~7 seconds for this
   extract) and `loaded graph at:/data/graph-cache`. `/info` returned all three existing profiles,
   container healthy.
2. Restored `foot` to `config.yml` (profile, `profiles_lm` entry, and `foot_access` /
   `foot_average_speed` / `foot_road_access` in `graph.encoded_values`) and recreated again. This
   failed identically to approaches 1-4, because `graph-cache` was now non-empty from step 1's
   import and GraphHopper loaded that instead of re-importing — same underlying mechanism, one layer
   later. Reverted to the known-good no-foot config to stop the resulting restart loop.
3. Wiped `/data/graph-cache`'s contents (`docker exec ... rm -rf /data/graph-cache/*`; cheap, since
   the volume holds only a derived index of the read-only-mounted `.osm.pbf`, not source data) and
   recreated with `foot` back in `config.yml`. Real import completed, container healthy, `/info`
   listed `foot` with all three new encoded values, and an actual `POST/GET /route?profile=foot`
   between two `/nearest`-snapped points returned a real turn-by-turn walking route.

Landed as: `compose.yml` (entrypoint `-o` flag), `graphhopper/config.yml` (restored `foot` profile
and encoded values), `graphhopper-maps/config-local.js.example` and the gitignored local
`config-local.js` (added `foot: {}`).

`flood-routing-frontend` was rebuilt the same day (image bakes `config-local.js` in at build time
via `cp config-local.js.example config-local.js`) and redeployed. Confirmed in the running UI: the
routing panel's profile picker now shows a "Walking" option alongside "Car" and the motorbike
icon, and selecting it and setting two points sends a `profile=foot` request end to end. Routing
itself then hit a separate, unrelated bug — see [[flood-route-missing-geom-column]] — not a
regression from this fix, since it reproduces identically for `car` and `motorbike`.

## Concerns

A raw `docker run` of the pinned image (bypassing `docker compose`) hung at ~100% CPU with no
import progress for several minutes, reproduced twice. Root cause unknown and not investigated
further since it's unrelated to the profile-rejection failure. Use
`docker compose up --force-recreate graphhopper` for any further testing on this blocker, not a
standalone `docker run`, to avoid re-triggering that separate issue.

## Related topics

- [[graphhopper-backend]]. The subsystem this blocks.
- `TODOS.md`'s "Pinned GraphHopper build rejects any new vehicle profile" item

## Status history

- **2026-09-14, open.** First reproduced while adding a `foot` profile. Confirmed not
  pedestrian-specific: a synthetic `bike_access` profile with no dependency on `foot` fails
  identically.
- **2026-09-22, still open.** No new attempt since 2026-09-14.
- **2026-09-23, resolved.** Root cause: the entrypoint script overrides `graph.location` via a JVM
  system property, so the app always loaded a graph frozen into the image, never the mounted
  volume. Fixed with `-o /data/graph-cache` on the entrypoint. Verified live: real import, `foot`
  registered with its three new encoded values, and an actual walking route returned.
