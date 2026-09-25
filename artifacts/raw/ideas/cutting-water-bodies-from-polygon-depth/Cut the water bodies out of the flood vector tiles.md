---
date_captured: <% tp.date.now("YYYY-MM-DD") %>
type: idea
status: unexplored
source:
subsystem:
tags:
  - idea
related: []
---

# <% tp.file.title %>

## Idea

1. currently the depth.tif includes all of the water bodies such as lakes, rivers, ponds, etc 
2. we need to cut these out of the vector tiles that serve on the front end so that user would not confused about the flooded areas 

## Why it might be worth it

user would not confused about the flooded areas 

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
