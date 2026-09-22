---
date: 2026-09-18
type: decision
branch: flood-tile-t6t7
status: active
tags: [graphhopper, routing]
related: ["[[2026-09-14]]"]
---

# Why the walking and truck routing profiles don't show in the frontend

Two vehicle profiles the user asked for, walking (`foot`) and truck, are both missing from
the routing UI as of 2026-09-18. The two have different causes.

## Truck: a config gap, not a bug

`floodmap/graphhopper-flood-road/graphhopper/config.yml` already registers a working `truck`
profile, backed by `truck_custom.json`, in both `profiles` and `profiles_lm`. Its flood-depth
block threshold was corrected from 50cm to 35cm on 2026-09-14
(`floodmap/graphhopper-flood-road/scripts/flood_utils.py`).

The frontend never asked for it. `floodmap/graphhopper-maps/config-local.js.example` lists
only two profiles:

```js
profiles: {
    motorbike: {},
    car: {},
},
```

Nothing blocks adding `truck: {}` here. The backend already serves the profile.

## Walking: blocked on a GraphHopper build issue

The `foot` profile is genuinely stuck. Work started on 2026-09-14: `flood_utils.py` got a
`VEHICLE_PROFILES["foot"]` entry at a 40cm depth threshold, matching the user's pedestrian-block
requirement, and `foot_custom.json` plus `foot_avoid_private_node_custom.json` were staged in
the GraphHopper config directory as trimmed copies of GraphHopper's own bundled `foot.json`.

The pinned GraphHopper image (`israelhikingmap/graphhopper`, digest pinned in `compose.yml`)
rejects any newly declared vehicle encoded value at startup, before OSM import runs:

```
Cannot compile expression: '<name>_access' not available
```

Four attempts failed the same way: GraphHopper's stock `foot.json`, a trimmed version dropping
`hike_rating` and `mtb_rating`, a further trim dropping `foot_priority`, and a synthetic
`bike_access` test profile with no dependency on `foot` at all. The last one rules out anything
foot-specific. This build cannot add any vehicle profile beyond the three already baked into the
current graph: `car`, `truck`, and `motorbike`.

`config.yml`'s `foot` block stays commented out, with a note pointing at the TODOS.md entry.
`config-local.js.example` has no `foot` entry either.

## What unblocks each one

Adding `truck: {}` to `config-local.js.example`'s `profiles` object and rebuilding the frontend
should surface truck routing immediately. No backend change is needed.

Walking needs the GraphHopper build issue resolved first, either by finding a different pinned
digest that accepts new encoded values or by diffing against upstream GraphHopper's
encoded-value factory for this exact snapshot. Once that's fixed, wiring `foot` in is a roughly
15-minute change: restore the `foot` entries in `config.yml` (`profiles`, `profiles_lm`,
`graph.encoded_values`), and add `foot: {}` to `config-local.js.example`. The backend logic
(`derive_areas()`, `build_custom_model()`) is vehicle-agnostic already and needs no further
change.

## Sources

- `artifacts/logs/2026-09-13.md`
- `artifacts/logs/2026-09-14.md`
- `artifacts/logs/2026-09-15.md`
- `artifacts/logs/2026-09-17.md`
- `artifacts/logs/2026-09-18.md`
- `TODOS.md`
- `floodmap/graphhopper-flood-road/graphhopper/config.yml`
- `floodmap/graphhopper-maps/config-local.js.example`
