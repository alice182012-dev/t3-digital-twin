---
date: 2026-10-08
type: plan
branch: modular
status: active
tags: [plan, sprint-plan, routing, paper, frontend, sprint-12, sprint-13]
related: ["[[sprint-plan-3]]", "[[sprint-plan-4]]", "[[US-090-093-routing-paper-experiments-stories]]", "[[frontend-mockup-recheck-stories]]", "[[carried-over-backlog]]", "[[paper-handoff-routing-and-system]]", "[[rain-replay-test-environment-stories]]", "[[core-output-hygiene-stories]]"]
---

# Plan: schedule the routing paper experiments and move the frontend

## Context

On 2026-10-08 the user decided: "From P1-P4 lets move them to sprint 12, and the front end can be sprint 13. We need to
finish the routing first." P1 to P4 are the four experiments of [[paper-handoff-routing-and-system]]. The frontend
recheck (`US-076` to `US-085`) and `US-033` sat in Sprint 12 of [[sprint-plan-3]].

## What changed

1. Four stories, `US-090` to `US-093`, written in [[US-090-093-routing-paper-experiments-stories]]. The next free ID in `Home.md` is
   `US-094`. The order is P1, P2, P3, P4.
2. Sprint 12 of [[sprint-plan-3]] now holds `US-086` to `US-093`: four M and four S rows. Its goal is to finish the
   routing. The Risks table, "Why these four sprints", the calendar notes, the `related` links, and the Status history
   follow.
3. The backlog row "Measure how many routes arrival-only closure would change" became `US-093`, and the row left the
   backlog table.
4. A new plan, [[sprint-plan-4]], covers Sprints 13 to 16, dated 2026-12-14 to 2027-01-10. A plan covers exactly four
   sprints, and [[sprint-plan-3]] ends with Sprint 12, so Sprint 13 cannot belong to it.
5. The frontend rows are placed by dependency (rule 3). Sprint 13: `US-076`, `US-085`, `US-079`, `US-080`. Sprint 14:
   `US-077`, `US-078`, `US-084`. Sprint 15: `US-081`, `US-082`. Sprint 16: `US-083`.
6. `US-033` carries to plan 5, because it reads `US-083`, which is in Sprint 16.
7. The `Sprint` field of every moved story is updated in [[frontend-mockup-recheck-stories]] and [[carried-over-backlog]].
   `sprint-plan.md` carries a `US-033` row, so that row is updated too. The one sentence in `TODOS.md` about the next
   sprint is corrected. The handoff table has the new IDs, and P5 is marked done.

## Decisions for the user

1. **Sprint 13 holds only four of the ten frontend rows.** The user said "the front end can be sprint 13". Six rows read the
   output of another row, and rule 3 puts them in later sprints. The alternative is to put them all in Sprint 13 and
   accept that they start before the screenshots of `US-076` exist.
2. **`US-033` has no sprint in plan 4.** The dependency chain is `US-076`, `US-077`, `US-082`, `US-083`, `US-033`, five
   links in four sprints. The user wrote Sprint 13. Ask the user to confirm the carry to plan 5.
3. **`US-092` reads the harness of `US-091` in the same sprint.** That bends rule 3 at the user's placement. The fallback
   is a move to Sprint 13 if the harness slips.

## Checks to run

- `grep -rn "US-09[0-3]" artifacts --include='*.md'` shows each ID in the epic file, `sprint-plan-3.md`, and
  `paper-handoff-routing-and-system.md`.
- `grep -n "next free" artifacts/Home.md` shows `US-094`.
- Open [[sprint-plan-3]] and [[sprint-plan-4]] in Obsidian and confirm the tables render.

## Status history

- **2026-10-08, active.** Written. Nothing is committed or pushed. `artifacts/raw/` is untouched, so
  `T3-Digital-Twin_Architecture.md` still says the mockup recheck is in Sprint 12 (lines 343 and 737). The user updates
  that file.
