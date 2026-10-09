---
date_drafted: 2026-10-09
type: user-story
us_id: "US-097"
story_label: "1"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P1
estimate: M
sprint: 12
subsystem: routing, frontend
related: ["[[EP-16-precaution-depth-routing]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Recommend a route that avoids the precaution depth, and keep the hard-limit route as a second option"
---

# US-097 Recommend a route that avoids the precaution depth, and keep the hard-limit route as a second option

As a driver, I want the recommended route to stay out of water that is half as deep as my vehicle's limit, and I still want to see the route that crosses it, so I can decide for myself.
Given a request with the time-aware flag on, when the backend plans, then it runs the sticky search with the hard limit first. If that route touches no road whose depth in the sticky window reaches the precaution depth, it is the only route and the second search is skipped. Otherwise the backend runs a second sticky search with the precaution depth. If that finds a route, it is the recommended route and the hard-limit route is the second option. If it finds none, the hard-limit route is the recommended route, flagged as passing through water. `POST /route` returns the options with their kind (`recommended`, `through_water`) and the depths that set them. The fraction is one setting, default 0.5, read from the vehicle profile owner of `US-074`.
Dependencies: `US-096` (`Done` in code), the offline sweep of `US-092` to confirm the fraction, and the user's go on the response contract.
Evidence: `us-097-through-water-route-output.png`.

## Evidence and details

**Evidence:** `US-096`, the fraction sweep of `US-092`, and the user's go on the response contract

**Details:**

![[us-097-through-water-route-output.png|120]]
