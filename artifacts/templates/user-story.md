---
date_drafted: <% tp.date.now("YYYY-MM-DD") %>
type: user-story
us_ids: []
status: draft
subsystem: 
sprint: 
source_ideas: []
related: []
tags: [user-story]
---

# <% tp.file.title %>

## User story

As a [type of user], I want to [task], so I can [objective].

## Priority

[priority level]

## Estimate

[story points, or a rough size]

## Acceptance criteria

Given [initial context], when [action performed], then [expected outcome].

## Status history

- **<% tp.date.now("YYYY-MM-DD") %>, draft.**

This is the simple story shape: one sprint, one objective. For a feature that spans
several sprints, split it into multiple stories under one epic instead of growing this
template. See [[user-story-types]] for the epic, thematic, and SAFe shapes and when
each one fits. If this story grew out of a note in `raw/ideas/`, list it in
`source_ideas`. Move `status` to `ready` once acceptance criteria are settled,
`in-progress` once work starts, or `done` once the acceptance criteria pass. Add a
dated bullet to "Status history" on every status change.

Fill `sprint` with the sprint number this story is scheduled into once a sprint plan
assigns one (see `sprint-plan-N.md` under `artifacts/docs/user-stories/`), and leave it
empty for a story that is still in the backlog. An epic-shaped story spans several
sprints, so it carries `Sprint: N` per row in its body instead of one frontmatter value;
see [[user-story-types]].

Give each story the next free `US-nnn` ID from the Conventions section of `Home.md`. Put
the ID in `us_ids` and after the story's label, as in `## User story (US-056)`, then raise
the next free number in `Home.md`.
