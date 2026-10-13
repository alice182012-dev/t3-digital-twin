---
date_drafted: 2026-10-13
type: user-story
us_id: "US-136"
title: "Explain the soak failures next to flooded edges"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Not started
kind: spike
priority: P2
estimate: S
sprint: 
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

## Evidence and details

Fill this when the story reaches `Done`.
