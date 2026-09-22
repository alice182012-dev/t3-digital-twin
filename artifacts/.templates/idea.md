---
date_captured: <% tp.date.now("YYYY-MM-DD") %>
type: idea
status: unexplored
source: 
subsystem: 
tags: [idea]
related: []
---

# <% tp.file.title %>

## Idea

One paragraph: what would change, in plain terms.

## Why it might be worth it

The concrete gap this closes, or the pain it removes. Cite specifics
(a memory rule that's currently unenforced, a manual step done repeatedly),
not generic upside.

## Cost-benefit summary

What adopting this costs (setup time, new failure modes, maintenance,
context/token overhead) against what it buys. Table if there are several
candidate pieces with different verdicts; prose if it's one thing.

## What's already covered

What existing tooling already does this job, partially or fully, so the
idea doesn't get re-litigated from zero next time it's picked up.

## Trigger to revisit

The condition that makes this worth doing now instead of leaving parked
(a recurring pain hit N times, a blocker that needs it, a slow day).

## Status history

- **<% tp.date.now("YYYY-MM-DD") %>, unexplored.** Captured from <source>.

Move `status` to `exploring` once the cost-benefit and what's-already-covered sections are
filled in, then to a decision once one is reached: `go` (worth building, moves to `marie-curie/` or a
PRD), `needs-clarification` (worth another look once a specific unknown resolves, name it in
"Trigger to revisit"), or `killed` (evaluated and rejected, keep the page as the record of why so
it isn't re-litigated). Add a dated bullet to "Status history" on every change.
