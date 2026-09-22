---
date_open: 2026-09-14
date_closed: 
type: blocker
status: open
severity: P2
subsystem: graphhopper
approaches_tried: 4
approaches_remaining: 2
tags: [blocker, graphhopper]
related: ["[[graphhopper-backend]]", "[[2026-09-14]]"]
last_updated: 2026-09-22
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

## Decision and explanation

Pending. Two untried directions, from `TODOS.md`'s matching item:

- Diff against upstream GraphHopper's actual encoded-value factory for this exact snapshot commit
  to find what changed.
- Try a different pinned digest or version instead of root-causing this one.

Once resolved, wiring up `foot` is a roughly 15-minute change: restore the `foot` entries in
`graphhopper/config.yml` (`profiles`, `profiles_lm`, `graph.encoded_values`, all still described in
that file's comments) and add `foot: {}` back to `graphhopper-maps/config-local.js.example`'s
`profiles`. No other code changes are needed; the icon and backend logic already exist and work.

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

Update `status` to `monitoring` if a fix is attempted but not yet confirmed, or `resolved` once a
`foot` profile actually starts; set `date_closed` at that point. Add a dated bullet above each time
the status changes or a new attempt is made, even if it fails.
