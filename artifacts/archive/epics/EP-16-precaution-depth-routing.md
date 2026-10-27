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

Story-level progress lines up to 2026-10-10 are in [[EP-16-precaution-depth-routing-history|the archived history]]. This section keeps plan-level changes only.

- **2026-10-09, draft.** Written at the user's request after the discussion of the cost band ([[BL-025-engine-has-no-depth-band-cost|engine-has-no-depth-band-cost]]). The user's rule: detour at 50 percent of the limit to protect assets, because the flood model is not validated, and still show the hard-limit route. IDs `US-097` and `US-098`. D-021.
