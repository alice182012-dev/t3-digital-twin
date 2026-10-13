---
date_drafted: 2026-10-13
type: user-story
us_id: "US-136"
title: "Explain the soak failures next to flooded edges"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Reviewed
kind: spike
priority: P2
estimate: S
sprint: 14
subsystem: routing, testing
source_ideas: []
related: ["[[graphhopper-backend]]", "[[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]]", "[[decision-log|D-044]]"]
tags: [user-story]
---

# US-136 Explain the soak failures next to flooded edges

As a developer, I want to know why three pairs of the soak `roads` check fail under the flood areas of `DEMO` mode, so I can tell a routing fault from the effect of the 22 m buffer.

On 2026-10-13 the check, with its dry control sent to GraphHopper ([[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]]), judged 79 pairs at the pinned step and failed 3.
A truck failed a `crosses` promise on edge `116434665:2` (15 cm).
A car and a truck failed a `found` promise on edge `400545823:1` (21 cm).
The flooded request found no route in either direction, and the dry control found one.
[[graphhopper-backend]] records that GraphHopper blocks a whole edge when any part of it meets a priority 0 polygon, and that the 22 m buffer widens the effect.
The question is whether the three failures are this effect, and so a limit of the neighbourhood rule of the pick, or a fault.
The timebox is one day in `marie-curie/`.
The answer goes into this story with a `D-nnn` decision.

Given the three pairs and the pinned run, when the blocked polygons of each request are read from `/flood/areas`, then the story names the polygon that closes each route and the edge of 30 cm or more that made it.

Dependencies: [[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]] is `Reviewed`.

## Status history

- **2026-10-13, draft.** Found when [[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]] ran on the server. It is in the backlog and has no `sprint`.
- **2026-10-13, Reviewed.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and answered the same day on read-only queries and requests against the server ([[decision-log|D-050]]). The three failures are a flaw of the pair selection and not a routing fault. The owner has not accepted it.

## Evidence and details

**Evidence:** `marie-curie/us136/result.json` and the script `marie-curie/us136/analyze.py` (scratch, not tracked by git).

**Details:**

1. The script reproduced the pairs of the check at the pinned step (run `20261011T001500`, 19:00 UTC, mode `DEMO`) with the same selection (`pick_roads`, 4 per bucket, oversample 5).
   For each pair it read `/flood/areas` for the vehicle (400 polygons for the truck, 450 for the car), sent the dry control straight to GraphHopper as in [[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]], and, for each blocked polygon (`b4`) that the dry route crosses, listed the edges at or above the vehicle's limit under it.
2. All three flooded requests answer 400 with "Connection between locations not found", in both directions. The dry control answers 200 with 70 and 38 points for the truck on `116434665:2`, and with 32 and 68 points for the car and the truck on `400545823:1`.
3. The start, the end, and the picked piece are in no polygon, and no edge at or above the limit lies within 60 m of them. So the neighbourhood of the piece is clear, as the pick intends.
4. Each dry route crosses 3 blocked polygons. Two of them cover edges that lie on the route, at distance 0.0 m: `1117859339:1` (109 cm), `1149080411:0` (108 cm), `1117859340:0` (146 cm), and `1483668388:0` (136 cm), against limits of 30 cm (car) and 35 cm (truck). The third polygon's nearest edge of 94 cm lies 26 m from the route, which can be the buffer of 22 m and not a deep road on the route.
5. Cause: the pick checks the neighbourhood of the piece (about 170 m), and the route between the two neighbours is longer and passes other deep roads. The flooded request refuses a route through roads that are 3 to 4 times deeper than the limit, which is correct.
6. For the `found` pairs on `400545823:1` the dry route does not cross the picked piece (`crosses` is false), so the pair does not test the piece at all.
7. The fix is [[US-138-skip-soak-pairs-whose-dry-route-crosses-other-blocked-roads|US-138]]: skip a pair when its dry route runs on another edge at or above the limit.
