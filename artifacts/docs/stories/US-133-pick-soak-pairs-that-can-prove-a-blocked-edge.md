---
date_drafted: 2026-10-13
type: user-story
us_id: "US-133"
title: "Pick soak pairs that can prove a blocked edge"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Not started
kind: story
priority: P2
estimate: S
sprint: 
subsystem: routing, testing
source_ideas: []
related: ["[[graphhopper-backend]]", "[[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]]", "[[lessons#L-013|L-013]]"]
tags: [user-story]
---

# US-133 Pick soak pairs that can prove a blocked edge

As a developer, I want the soak `roads` check to test the blocked promise, so a run that skips every blocked pair cannot pass.

On 2026-10-13 the check skipped all 51 blocked pairs of its 104, because the dry control route did not cross the picked edge ([[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]], details item 7).
A skipped pair shows no kept promise, and the run reported 0 failures.
The story picks pairs whose dry route must cross the edge, for example the two ends of an edge that is the only way across, and it fails a run that has no blocked pair to judge.

Given a run with edges at or above a vehicle's limit, when the check runs, then at least one blocked pair per vehicle is judged and not skipped.
Given a run with no judged blocked pair, then the check reports it and exits with a failure.

Dependencies: [[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]] is `Done`.

## Status history

- **2026-10-13, draft.** Found during the server checks of [[SPR-014-finish-the-remaining-backend|SPR-014]]. The owner asked for a story on the same day.

## Evidence and details

Fill this when the story reaches `Done`.
