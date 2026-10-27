---
date_captured: <% tp.date.now("YYYY-MM-DD") %>
type: lesson
status: active
subsystem: 
source_blockers: []
tags: [lesson]
related: []
---

# <% tp.file.title %>

Name this file L-nnn-<slug>.md. Take nnn from the next free number in the Conventions of Home.md.

## Rule

One or two sentences, stated as a check to run or a thing to do, not a description of what
happened. "Before varying a config, read the entrypoint that consumes it", not "the entrypoint
mattered more than the config did."

## Why

The concrete incident this came from: what was tried, what looked true but wasn't, and what the
real cause turned out to be. Link the blocker page in `source_blockers` instead of retelling its
full approach-by-approach history here.

## How to apply

The condition that means this rule is live: what kind of task, what kind of failure, what to check
first. Specific enough that a later session can tell whether it applies without re-reading the
source blocker.

## Source blockers

- 

## Status history

- **<% tp.date.now("YYYY-MM-DD") %>, active.** Captured from <blocker>.

Set `status` to `retired` if a later incident shows the rule was wrong or too narrow, and explain
why in a new status-history line rather than deleting the entry.
