---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: architecture-backend
source_blockers: []
tags: [lesson, prd, verification]
related: ["[[flood-routing-mockup-frontend-gap]]", "[[t3-digital-twin-architecture-gaps]]"]
---

# Verify a stated answer resolves the question before recording it as a Decision

## Rule

When a user answers a Risk or open question with a short pointer ("A: flood_road_values"), check
that the thing they named can actually do what the question asked, before writing it into the
PRD's Decisions table as settled. A short answer can name the wrong noun in good faith.

## Why

`flood-routing-mockup-frontend-gap.md`'s Risks and open questions asked where the place-depth
popup's arbitrary-point depth lookup should come from. The user answered "A: flood_road_values",
and that got written into Decisions as the settled source. It wasn't checked against what the risk
actually asked: an arbitrary-point query, at whatever spot a user taps, not necessarily on a road.
`flood_road_values` only has depth at road segments. The user caught this themselves in the next
session turn ("we cant use it for the depth on each point of the map"), which forced a correction
across the Decision row, the Dependencies section, and a cross-reference in
`t3-digital-twin-architecture-gaps.md`.

## How to apply

Before writing a stated answer into a Decisions table, restate the original question in one clause
and check the answer against it directly: does "flood_road_values" cover "depth at an arbitrary
tapped point", not "depth somewhere in this general area" or "depth on the nearest road". If the
check takes more than a sentence to confirm, that's a sign the answer needs verifying against the
actual schema or code before transcribing it, not after.

## Source blockers

- None. Surfaced from a PRD Decisions-table correction, not a resolved blocker.

## Status history

- **2026-09-23, active.** Captured after correcting `flood-routing-mockup-frontend-gap.md`'s goal
  1 data source from `flood_road_values` to `GET /flood/points`, following the user's own
  follow-up question.
