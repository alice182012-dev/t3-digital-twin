---
date_discovered: 2026-09-14
type: blocker
status: open
severity: P2
subsystem: graphhopper
related: ["[[graphhopper-backend]]", "[[2026-09-14]]"]
last_updated: 2026-09-22
---

# GraphHopper pinned image rejects any new vehicle profile

The pinned `israelhikingmap/graphhopper` build (digest in `compose.yml`) fails at startup with
`Cannot compile expression: '<name>_access' not available` for any vehicle encoded value beyond
the three already in the working graph. This blocks adding a `foot` profile and any other new
vehicle profile. Full root-cause detail, the four approaches already tried, and what's ready to go
once this clears live in [[graphhopper-backend]]'s "pinned image and routing profile blocker"
section and in `TODOS.md`'s matching item.

## Status history

- **2026-09-14, open.** First reproduced while adding a `foot` profile. Confirmed not
  pedestrian-specific: a synthetic `bike_access` profile with no dependency on `foot` fails
  identically.
- **2026-09-22, still open.** No new attempt since 2026-09-14. `foot_custom.json` and
  `foot_avoid_private_node_custom.json` remain ready and untested against a fixed build.

Update `status` to `monitoring` if a fix is attempted but not yet confirmed, or `resolved` once a
`foot` profile actually starts. Add a dated bullet above each time the status changes or a new
attempt is made, even if it fails, so the history of what's been tried doesn't have to be
reconstructed from logs again.
