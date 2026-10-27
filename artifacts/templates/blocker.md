---
date_open: <% tp.date.now("YYYY-MM-DD") %>
date_closed: 
type: blocker
status: open
severity: P2
subsystem: 
approaches_tried: 0
approaches_remaining: 
tags: [blocker]
related: []
last_updated: <% tp.date.now("YYYY-MM-DD") %>
---

# <% tp.file.title %>

Name this file BL-nnn-<slug>.md. Take nnn from the next free number in the Conventions of Home.md.

## Description

What's blocked, and what fails when you hit it (the exact error, if there is one).

## Why this matters

What this blocks downstream, and who or what is waiting on it.

## Approaches tried

### Approach 1

What was tried, and what happened. Bump `approaches_tried` in the frontmatter when you add one of
these.

## Decision and explanation

Pending. Fill in once a fix is chosen: what was decided, and why that option over the others in
"Approaches tried."

## Concerns

Anything that could resurface after this closes, or a risk the chosen fix doesn't fully cover.
Delete this section if there's nothing to flag.

## Related topics

- 

## Status history

- **<% tp.date.now("YYYY-MM-DD") %>, open.** 

Update `status` to `monitoring` once a fix is attempted but not yet confirmed, or `resolved` once
it's confirmed working; set `date_closed` at that point too. Add a dated bullet here on every
status change or new attempt, including a failed one, so the history doesn't have to be
reconstructed from logs later.
