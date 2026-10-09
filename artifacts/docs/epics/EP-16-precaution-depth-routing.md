---
date_drafted: 2026-10-09
type: user-story
us_ids: ["US-097", "US-098"]
status: draft
subsystem: routing, frontend
source_ideas: []
related: ["[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[SP-04-frontend-recheck|sprint-plan-4]]", "[[decision-log]]", "[[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]]", "[[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]]", "[[BL-025-engine-has-no-depth-band-cost|engine-has-no-depth-band-cost]]", "[[sticky-closure-proof]]"]
tags: [user-story, epic, routing, precaution-depth]
---

# Epic: precaution depth routing

The flood model is not validated. D-021 therefore gives each vehicle a precaution depth of 50 percent of its hard limit (motorbike 10 cm, car 15 cm, truck 17.5 cm, foot 20 cm). The recommended route avoids roads at or above the precaution depth. The route that is planned with the hard limit stays available as a second option. Each row carries Priority, Status, Estimate, and Sprint, as an extension of the base Epic shape in [[user-story-types]] (`.claude/CLAUDE.md`, rule 2).

- [[US-097-recommend-a-route-that-avoids-the-precaution|US-097]] Recommend a route that avoids the precaution depth, and keep the hard-limit route as a second option. Story 1.
- [[US-098-show-the-recommended-route-and-the-through|US-098]] Show the recommended route and the through-water option in the app. Story 2.

## Status history

- **2026-10-09, draft.** Written at the user's request after the discussion of the cost band ([[BL-025-engine-has-no-depth-band-cost|engine-has-no-depth-band-cost]]). The user's rule: detour at 50 percent of the limit to protect assets, because the flood model is not validated, and still show the hard-limit route. IDs `US-097` and `US-098`. D-021.
- **2026-10-09, reviewed.** The user approved the response contract. Built on `modular`: path 0 is the recommended route, path 1 the through-water route, hints `td.kinds`, `td.limit_cm`, `td.precaution_cm`, profile hint `td_precaution_fraction` (default 0.5), second search only when the limit route touches the precaution depth. 137 Java tests passed on GitHub Actions (run 37885851481). The server image is rebuilt at the next rollout, and the flag is off at rest. `US-098` can read the contract.
- **2026-10-09, done.** The rollout rebuilt the server images from `modular` (`11f6373`) and every script check passed. With the flag on, `POST /route` for the "long" trip with the truck and foot profiles returned 2 paths and `td.kinds: "recommended,through_water"`; the same trip with motorbike and car returned 1 path, `td.kinds: "recommended"`. Evidence: `us-097-through-water-route-output.png`.
