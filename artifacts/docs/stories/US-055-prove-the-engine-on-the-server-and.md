---
date_drafted: 2026-09-29
type: user-story
us_id: "US-055"
story_label: "R10"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: M
sprint: 10
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Prove the engine on the server and roll it out"
---

# US-055 Prove the engine on the server and roll it out

As the team, I want evidence on the server before the flag goes on, so the change ships with numbers and not
hopes.
Given the deployed image and a real run, when the four scenarios run for `motorbike` and `car`, then the
results pass the checker. Given the baseline from Story R1 and the factor the user sets, when the p50 and
p95 of `POST /route` are measured, then both are inside the factor. Given a fixed set of pairs, when the
same pairs run against today's model and the reference, then the percentage of pairs whose route changes
and the median detour ratio are recorded. The concept page [[graphhopper-backend]] and
[[BL-011-routing-not-time-aware|routing-not-time-aware]] are updated, and the blocker moves to `resolved` only with this evidence.
Priority: P0. Status: Done. Estimate: M. Sprint: 10. Dependencies: Stories R6, R7, R9, E7.
Tooling built on 2026-10-05, tests first: `scripts/routing_proof/routing_proof.py` (25 tests, four changes make tests fail), `pairs.json` (24 pairs inside the model border), and `rollout.ps1` (untested, it needs the server). The evidence step is one run of `rollout.ps1` after the 48-hour replay ends, plus `scenario-check.sh` from the Mac. Plan: [[engine-server-proof-and-rollout]]. Gate cleared:
the user set the latency factor of 2 on 2026-10-02, so the p50 and p95 of each trip and vehicle stay within 2 times the baseline of Story R1.

## Evidence and details

**Evidence:** Stories R6, R7, R9, E7. Gate cleared 2026-10-02: the user set the latency factor to 2

**Details:**

![[us-055-rollout-results-check-output.png\|120]]
