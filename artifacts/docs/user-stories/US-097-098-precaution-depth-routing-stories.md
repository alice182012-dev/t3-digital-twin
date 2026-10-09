---
date_drafted: 2026-10-09
type: user-story
us_ids: ["US-097", "US-098"]
status: draft
subsystem: routing, frontend
source_ideas: []
related: ["[[sprint-plan-3]]", "[[sprint-plan-4]]", "[[decision-log]]", "[[time-aware-routing-engine-stories]]", "[[US-090-093-routing-paper-experiments-stories]]", "[[engine-has-no-depth-band-cost]]", "[[sticky-closure-proof]]"]
tags: [user-story, epic, routing, precaution-depth]
---

# Epic: precaution depth routing

The flood model is not validated. D-021 therefore gives each vehicle a precaution depth of 50 percent of its hard limit (motorbike 10 cm, car 15 cm, truck 17.5 cm, foot 20 cm). The recommended route avoids roads at or above the precaution depth. The route that is planned with the hard limit stays available as a second option. Each row carries Priority, Status, Estimate, and Sprint, as an extension of the base Epic shape in [[user-story-types]] (`.claude/CLAUDE.md`, rule 2).

- **Story 1 (US-097): Recommend a route that avoids the precaution depth, and keep the hard-limit route as a second option.**
  As a driver, I want the recommended route to stay out of water that is half as deep as my vehicle's limit, and I still want to see the route that crosses it, so I can decide for myself.
  Given a request with the time-aware flag on, when the backend plans, then it runs the sticky search with the hard limit first. If that route touches no road whose depth in the sticky window reaches the precaution depth, it is the only route and the second search is skipped. Otherwise the backend runs a second sticky search with the precaution depth. If that finds a route, it is the recommended route and the hard-limit route is the second option. If it finds none, the hard-limit route is the recommended route, flagged as passing through water. `POST /route` returns the options with their kind (`recommended`, `through_water`) and the depths that set them. The fraction is one setting, default 0.5, read from the vehicle profile owner of `US-074`.
  Priority: P1. Status: Reviewed. Estimate: M. Sprint: 12 ([[sprint-plan-3]]).
  Dependencies: `US-096` (`Done` in code), the offline sweep of `US-092` to confirm the fraction, and the user's go on the response contract.
  Evidence: None yet.

- **Story 2 (US-098): Show the recommended route and the through-water option in the app.**
  As a driver, I want to see both routes with a label that says the second one passes through water between the precaution depth and my limit.
  Given a response with two options, when the route panel opens, then it shows the recommended route first and the through-water route as a second tab with its label and its deepest road. With one option, it shows one route. The no-route message changes to match D-021.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 14 ([[sprint-plan-4]]).
  Dependencies: `US-097`, `US-076`, and the design of the no-route state in `US-084`.
  Evidence: None yet.

## Status history

- **2026-10-09, draft.** Written at the user's request after the discussion of the cost band ([[engine-has-no-depth-band-cost]]). The user's rule: detour at 50 percent of the limit to protect assets, because the flood model is not validated, and still show the hard-limit route. IDs `US-097` and `US-098`. D-021.
- **2026-10-09, reviewed.** The user approved the response contract. Built on `modular`: path 0 is the recommended route, path 1 the through-water route, hints `td.kinds`, `td.limit_cm`, `td.precaution_cm`, profile hint `td_precaution_fraction` (default 0.5), second search only when the limit route touches the precaution depth. 137 Java tests passed on GitHub Actions (run 37885851481). The server image is rebuilt at the next rollout, and the flag is off at rest. `US-098` can read the contract.
