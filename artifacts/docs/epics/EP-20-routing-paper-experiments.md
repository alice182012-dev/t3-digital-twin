---
date_drafted: 2026-10-10
type: epic
epic_id: "EP-20"
theme: paper
status: active
subsystem: routing, paper
tags: [epic, paper, experiments, spike]
related: ["[[paper-handoff-routing-and-system]]", "[[sticky-c-lite-routing]]", "[[sticky-closure-proof]]", "[[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]]", "[[decision-log]]"]
---

# EP-20 Routing paper experiments

## Goal

The experiments and proofs the routing paper needs: the correctness proof of the sticky-closure search, the rate at which a single-timestep route meets a closed road, how the vehicle limits change the result, and the cost of sticky closure against an arrival-only reference.

## Why

The paper claims that a time-aware route is safer than a single-step route. Each claim needs a measurement on the real graph. The handoff page ([[paper-handoff-routing-and-system]]) lists what the paper needs.

## Dependencies and assumptions

- The measurements read the edge depth tables of a rain replay ([[EP-17-flood-data-pipeline-and-core-output|EP-17]]) and the engine ([[EP-18-time-aware-routing-engine|EP-18]]).
- The flood model is not validated, so the paper reports the engine's behavior and not a forecast skill.
- Most stories here are spikes (`kind: spike`). A spike ends with an answer in the story and a decision in [[decision-log]]. It does not need a UI screenshot.

## Definition of done

1. Each paper claim has a story with a recorded result and a decision.
2. The scripts that produced a number are under `marie-curie/` or promoted to `scripts/`, and the story names the command that regenerates the number.

## Risks and open questions

- `US-091` needed a replay of the storm with the `US-101` fix, because the backend keeps flood areas for only 8 runs by default. The replay of 2026-10-10 (`US-102`) supplied it.

## Stories

```dataview
TABLE title AS "Story", kind AS "Kind", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE contains(string(epic), "EP-20")
SORT file.name ASC
```

## Status history

- **2026-10-10, active.** Created from the Scrum adoption ([[decision-log|D-024]]). It replaces the archived `EP-14`. The six stories are tagged `kind: spike`.
