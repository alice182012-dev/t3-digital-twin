---
date: <% tp.date.now("YYYY-MM-DD") %>
type: sprint
sprint_id: "SPR-nnn"
sprint: 
start_date: 
end_date: 
status: planning
tags: [sprint]
related: []
---

# SPR-nnn Sprint N: <% tp.file.title %>

## Sprint goal

One sentence, written by the product owner at planning. The goal does not change during the sprint.

## Planning

- **Velocity.** Points Done in the last three sprints, from [[Velocity]]: A, B, C. Forecast: N points for the two weeks.
- **Picked stories.** The sprint backlog below. The total of the picked estimates is N points.
- **Open decisions.** Questions the product owner answers at planning. Remove each line when it is answered.

## Sprint backlog

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = N
SORT priority ASC, file.name ASC
```

## Review

Fill this on the last day. Walk through each story that is `Done` by its evidence screenshot, and record the product owner's accept or reject.

- **Goal met:** yes or no, with one sentence.
- **Points delivered:** N of N forecast.
- **Not done:** each story that left the sprint, back to the backlog with `sprint` cleared.

## Retrospective

Three bullets and one action. Check the last retrospective's action first.

- **Worked:**
- **Did not work:**
- **Action:** a story, a rule change, or an `L-nnn` lesson.

## Refinement for the next sprint

The top of the backlog after this review: the order, the stories split, and the questions to answer.

## Status history

Sprint-level changes only: the sprint started, a story left the sprint to protect the goal, the sprint ended. Story progress lives in the story file.

<!--
- Name the file SPR-nnn-<slug>.md in artifacts/docs/sprints/. nnn is the sprint number with
  three digits. Take the slug from the sprint goal.
- A sprint is two weeks, Monday to the Sunday of the next week, and the next sprint starts the next Monday.
  Planning picks stories until their points reach the forecast. The calendar does not decide the count.
- sprint: the number written in the `sprint` field of the picked stories.
- status: planning, active, or done.
- A story reaches this sprint only by planning. Setting `sprint` on a story is the pick.
-->
