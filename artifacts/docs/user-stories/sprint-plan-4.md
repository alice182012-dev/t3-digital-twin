---
date: 2026-10-08
type: plan
status: active
plan_number: 4
start_date: 2026-12-14
end_date: 2027-01-10
tags: [user-story, sprint-plan, frontend]
related: ["[[sprint-plan-3]]", "[[sprint-plan-2]]", "[[frontend-mockup-recheck-stories]]", "[[carried-over-backlog]]", "[[frontend-mockup-recheck-and-sprint-11-start]]", "[[US-090-093-routing-paper-experiments-stories]]", "[[schedule-routing-paper-experiments-and-move-frontend]]"]
---

# Sprint plan 4: the frontend recheck against the mockup

The frontend recheck, moved out of [[sprint-plan-3]] on 2026-10-08 so the routing work finishes first. This plan follows
[[sprint-plan-3]] (Sprints 9 to 12), so its sprint numbers continue at 13. It covers four weeks (`.claude/CLAUDE.md`,
rule 10). Its rows are the ten stories of [[frontend-mockup-recheck-stories]] (`US-076` to `US-085`).

## Why these four sprints

Four sprints because a plan covers four weeks. Sprint 12 of [[sprint-plan-3]] was the last sprint of that plan, so the
user's decision of 2026-10-08, "the front end can be sprint 13", starts a new plan. The user's reason was: "We need to
finish the routing first."

The order follows the dependencies of the rows (rule 3). A story that reads the output of another story lands in a
later sprint than that story.

1. `US-076` compares the live app with the mockup, and its screenshots feed `US-077`, `US-078`, and `US-084`.
2. `US-077` fixes the chart columns and the tab text, which `US-081` and `US-082` build on.
3. `US-082` adds time and depth to the tabs, which `US-083` (the mobile layout) covers.
4. `US-033` (`DESIGN.md`) extracts tokens from the UI that `US-077` to `US-083` finish.

That chain is `US-076`, then `US-077`, then `US-082`, then `US-083`, then `US-033`. It has five links and the plan has
four sprints. The first four links fill Sprints 13 to 16, and `US-033` carries to plan 5. Sprint 13 holds every row with
no unresolved dependency, as the user asked.

Calendar, from `start_date` in the frontmatter:

| Sprint | Start | End | Actual start | Actual end |
| ------ | ----- | --- | ------------ | ---------- |
| 13 | 2026-12-14 | 2026-12-20 |  |  |
| 14 | 2026-12-21 | 2026-12-27 |  |  |
| 15 | 2026-12-28 | 2027-01-03 |  |  |
| 16 | 2027-01-04 | 2027-01-10 |  |  |

- **Sprint 13** compares the app with the mockup and does the three rows with no dependency.
- **Sprint 14** matches the chart, the tab text, the pin names, and the two states the mockup lacks.
- **Sprint 15** adds the limit line and the tab details.
- **Sprint 16** builds the mobile layout and absorbs slips.

The dates follow the Monday start of the plan, one week per sprint, with no gap after Sprint 12 (2026-12-13). The
sprints may start earlier at the user's request, as Sprints 5 to 12 did.

Each story's Status is `Not started`, `In progress`, `Reviewed`, `Blocked`, or `Done`. Each story carries the same
Status in its epic file. Update both together. A story reaches `Done` only with evidence and details in both places.
A UI story takes its screenshot from the running UI (rule 8).

## Sprint 13: compare with the mockup and the independent rows

**Dates:** 2026-12-14 to 2026-12-20 (Monday to Sunday)

**Sprint goal:** the live app and the mockup are captured side by side at 1366x768, and the three rows that need no
other row (the page name, the legend label, and the client timeout) are done.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-076 | P1 | Compare the live app with the mockup in Aside at 1366x768 | S | [[frontend-mockup-recheck-stories]] 1 | None. Best after `US-055` | None yet | - | Not started |
| US-085 | P2 | Time out a route request in the client | S | [[frontend-mockup-recheck-stories]] 10 | None | None yet | - | Not started |
| US-079 | P3 | Name the page "Floodmap" and remove the "Powered by GraphHopper" line | XS | [[frontend-mockup-recheck-stories]] 4 | None | None yet | - | Not started |
| US-080 | P3 | Keep "As of" and bring the `US-007` record in line | XS | [[frontend-mockup-recheck-stories]] 5 | None | None yet | - | Not started |

## Sprint 14: match the chart, the tabs, the pins, and the missing states

**Dates:** 2026-12-21 to 2026-12-27 (Monday to Sunday)

**Sprint goal:** the chart columns, the tab text, and the pin labels match screen 2e, and the no-route and "wait until"
states have an approved design.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-077 | P2 | Match the depth chart columns and the route tab text to screen 2e | S | [[frontend-mockup-recheck-stories]] 2 | `US-076` (Sprint 13) | None yet | - | Not started |
| US-078 | P2 | Show the place names on the start and destination pins | S | [[frontend-mockup-recheck-stories]] 3 | `US-076` (Sprint 13) | None yet | - | Not started |
| US-084 | P2 | Design the no-route and "wait until" states, then match the UI to the design | S | [[frontend-mockup-recheck-stories]] 9 | `US-076` (Sprint 13), `US-055` ([[sprint-plan-3]] Sprint 10) | None yet | - | Not started |
| US-098 | P2 | Show the recommended route and the through-water option in the app | S | [[US-097-098-precaution-depth-routing-stories]] 2 | `US-097`, `US-076` (Sprint 13), and the design of `US-084` | None yet | - | Not started |

## Sprint 15: the limit line and the tab details

**Dates:** 2026-12-28 to 2027-01-03 (Monday to Sunday)

**Sprint goal:** the chart marks the selected mode's depth limit, and each route tab shows its travel time and its
maximum depth.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-081 | P3 | Draw a second dashed line for the selected mode's depth limit | S | [[frontend-mockup-recheck-stories]] 6 | `US-077` (Sprint 14), `US-074` ([[sprint-plan-3]] Sprint 11, `Done`) | None yet | - | Not started |
| US-082 | P3 | Show the travel time and the maximum depth on each route tab | S | [[frontend-mockup-recheck-stories]] 7 | `US-077` (Sprint 14) | None yet | - | Not started |

## Sprint 16: the mobile layout, and the slip buffer

**Dates:** 2027-01-04 to 2027-01-10 (Monday to Sunday)

**Sprint goal:** screen 2e fits a 390 px screen. The sprint also absorbs slips from Sprints 13 to 15.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-083 | P3 | Build a mobile version of screen 2e | M | [[frontend-mockup-recheck-stories]] 8 | `US-077` (Sprint 14), `US-078` (Sprint 14), `US-082` (Sprint 15) | None yet | - | Not started |

## Carried to plan 5

These rows have no sprint number. They do not fit the four weeks of this plan (rule 10), and no risk blocks them.

| Item | Priority | Story | Estimate | Epic | Why it has no sprint | Status |
| ---- | -------- | ----- | -------- | ---- | -------------------- | ------ |
| US-033 | P3 | Write a project `DESIGN.md` with real design tokens | M | [[carried-over-backlog]] Story 2 | It extracts tokens from the UI that `US-077` to `US-083` finish. `US-083` is in Sprint 16, the last sprint of this plan, so `US-033` belongs to the first sprint of `sprint-plan-5.md`. It blocks nothing. | Not started |

## Backlog

Nothing here has a sprint number because of an open risk. No row is in this state.

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Sprint 13 starts before `US-055` is `Done` | `US-084` reads the real "wait until" text from the backend, and `US-076` is best taken with the flag on | `US-055` is in [[sprint-plan-3]] Sprint 10 and has only DAG-timing pieces open. `US-084` is in Sprint 14, one sprint after `US-076`, which gives `US-055` more time. |
| The dependency chain has five links and the plan has four sprints | `US-033` cannot land in this plan | `US-033` carries to plan 5 and blocks nothing. If the user wants `DESIGN.md` earlier, its dependencies relax to the rows done by then, and the user decides. |
| The user placed the frontend in Sprint 13 and rule 3 moves most rows to Sprint 14 to 16 | Sprint 13 holds fewer rows than the user may expect | Sprint 13 holds every row with no unresolved dependency. Moving `US-077` or `US-078` into Sprint 13 means they start before the screenshots of `US-076` exist, which the user decides. |
| `US-083` (M) is the only row of Sprint 16, and it needs an approved mobile layout | A slip in the layout approval moves the row out of the plan | Sprint 16 also absorbs slips from Sprints 13 to 15. A slip beyond that moves to plan 5. |
| The UI changes after `US-033` extracts tokens | The tokens go stale | `US-033` stays after `US-083`, so it extracts from the final UI. |
| A row of [[sprint-plan-3]] Sprint 12 slips into Sprint 13 | Sprint 13 grows | `US-087` and `US-086` are the first rows to move from Sprint 12 to Sprint 13, with the user's go. Sprint 13 has room for them, because it holds two S and two XS rows. |

## Definition of done for a story

The same as [[sprint-plan-2]]: acceptance criteria pass where they say so, tests pass, the concept page is updated with
`last_updated` bumped, and a screenshot or rendered output plus numbered details are recorded in the epic file and in
this plan. A UI story takes its screenshot from the running UI. Test points stay inside the model border
(`.claude/CLAUDE.md`).

## Status history

- **2026-10-08, active.** Created at the user's request: "From P1-P4 lets move them to sprint 12, and the front end can be
  sprint 13. We need to finish the routing first." [[sprint-plan-3]] ends with Sprint 12, so Sprint 13 starts a new plan
  of four sprints (13 to 16), dated 2026-12-14 to 2027-01-10. The plan number is 4, because [[sprint-plan]],
  [[sprint-plan-2]], and [[sprint-plan-3]] come before it.
- **2026-10-08, active.** `US-076` to `US-085` moved here from Sprint 12 of [[sprint-plan-3]] and were placed by
  dependency (rule 3). Sprint 13: `US-076`, `US-085`, `US-079`, `US-080`. Sprint 14: `US-077`, `US-078`, `US-084`.
  Sprint 15: `US-081`, `US-082`. Sprint 16: `US-083`. The user placed the whole frontend in "sprint 13", and the
  dependencies move six rows later. The user is asked to confirm.
- **2026-10-08, active.** `US-033` (`DESIGN.md`) moved from Sprint 12 of [[sprint-plan-3]] to "Carried to plan 5". Its
  dependency `US-083` is in Sprint 16, the last sprint of this plan. The user is asked to confirm.
