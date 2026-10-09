---
date_drafted: <% tp.date.now("YYYY-MM-DD") %>
type: user-story
us_id: "US-nnn"
title: ""
epic: ""
status: Not started
kind: story
priority: P2
estimate: S
sprint: 
subsystem: 
source_ideas: []
related: []
tags: [user-story]
---

# US-nnn <% tp.file.title %>

As a [type of user], I want to [task], so I can [objective].

A spike (`kind: spike`) states a question and a timebox here instead, and ends with an answer and a decision.

Given [initial context], when [action performed], then [expected outcome].

Dependencies: [story IDs, or None].

## Status history

- **<% tp.date.now("YYYY-MM-DD") %>, draft.**

## Evidence and details

Fill this when the story reaches `Done`. **Evidence** is a screenshot saved under `artifacts/docs/stories/evidence/` and embedded with `![[name.png]]`. **Details** is a numbered list: what was built, how, why, and what it changes for dependent stories.

<!--
Name the file US-nnn-<slug>.md in artifacts/docs/stories/. Take nnn from the next free
number in the Conventions of Home.md, and raise that number.
- kind: story (user value), spike (a question with a timebox), or bug (a defect).
- status: Not started (in the backlog), Ready, In progress, Reviewed, Blocked, Done, or Superseded.
  Ready means the story passes INVEST: independent, negotiable, valuable, estimable, small (not L),
  and testable. See the Definition of ready in [[scrum-framework]].
- sprint: the sprint number, set only at sprint planning. Empty means the story is in the
  backlog. A story that is not Done at the sprint review gets its sprint cleared.
- estimate: XS=1, S=2, M=3, L=5 points. Split a story rated L before it enters a sprint.
- epic: a link to the EP-nn file, empty for a standalone story.
Do not repeat priority, status, estimate, or sprint in the story body. The frontmatter is their one home.
If the story grew out of a note in raw/ideas/, list it in source_ideas.
-->
