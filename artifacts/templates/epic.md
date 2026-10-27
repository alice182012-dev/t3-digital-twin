---
date_drafted: <% tp.date.now("YYYY-MM-DD") %>
type: epic
epic_id: "EP-nn"
theme: 
status: active
subsystem: 
tags: [epic]
related: []
---

# EP-nn <% tp.file.title %>

## Goal

One paragraph. What the epic delivers and for whom.

## Why

The problem the epic fixes, in a few sentences. Cite the file, blocker, or decision that shows it.

## Dependencies and assumptions

Every fact the design relies on that is not visible from reading the code cold.

## Definition of done

Operational checks, run in the environment that matters (usually the server). Each reads "Given, when, then". A proxy such as "it compiles" is not a check.

## Risks and open questions

A risk that blocks a story gets a blocker page. Link it here.

## Stories

```dataview
TABLE title AS "Story", kind AS "Kind", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE contains(string(epic), "EP-nn")
SORT file.name ASC
```

## Status history

Plan-level changes only: a story added, split, moved to another epic, or dropped. Story progress lives in the story file.

<!--
- Name the file EP-nn-<slug>.md in artifacts/docs/epics/. Take nn from the next free number in
  the Conventions of Home.md, and raise that number.
- An epic is a body of work that takes weeks and holds several stories. A group with no shared
  goal is a backlog, not an epic. Keep the number of epics small.
- theme: the long-running goal the epic serves (for example flood-data, routing, frontend, paper).
- status: active, done, or parked.
- The epic replaces the retired PRD. Goal, Why, Dependencies, and Definition of done live here.
-->
