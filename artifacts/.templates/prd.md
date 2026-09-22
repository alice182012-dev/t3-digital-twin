---
date_drafted: <% tp.date.now("YYYY-MM-DD") %>
type: prd
status: draft
subsystem: 
source_ideas: []
tags: [prd]
related: []
---

# <% tp.file.title %>

## Problem

What's broken or missing today, for whom, and what it costs them. Cite a specific incident, log
entry, or blocker page instead of a general pain. If this PRD grew out of a note in
`raw/ideas/`, list it in `source_ideas` (that file's `[[wikilink]]`) instead of retyping its
argument here.

## Goals

What this must achieve, stated so each one is checkable. One item, one testable outcome.

## Non-goals

What this deliberately doesn't cover, so scope doesn't creep back in mid-build.

## Dependencies and assumptions

Every fact this design relies on that isn't visible from reading the code cold: a build context
that has to exist, a flag an entrypoint has to receive, a volume that has to be the one actually
mounted, a service another component silently depends on. State each as a fact that could turn
out false, not a hope. This is the section [[graphhopper-vehicle-profile-rejection]] and
[[storage-backend-build-context-missing]] would have needed to exist before either blocker did.

## Definition of done

An operational check, not a proxy. "The container starts with no errors" is a proxy. "A real
`POST /route?profile=foot` request between two snapped points returns a route" is the check that
actually closed [[graphhopper-vehicle-profile-rejection]]. State what to run and what result
confirms it. Given/When/Then is a useful shape for this, as plain prose, not as a separate syntax:
given the starting state, when this action runs, then this is the result that confirms it worked.

## Risks and open questions

What could go wrong, and what isn't decided yet. Link a blocker page if one already exists for a
specific risk instead of restating it here.

## Rollback

What to revert, and to what state, if this turns out wrong after shipping.

## Status history

- **<% tp.date.now("YYYY-MM-DD") %>, draft.** 

Update `status` to `approved` once goals and definition of done are settled, `in-progress` once
implementation starts (link the `claude-plan/` entry in `related`), `shipped` once the definition
of done is confirmed, or `abandoned` if dropped. Add a dated bullet to "Status history" on every
status change.
