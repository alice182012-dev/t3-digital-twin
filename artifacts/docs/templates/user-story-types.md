---
date: 2026-09-23
type: reference
status: active
tags: [user-story, template, reference]
related: [[user-story]], [[prd]]
source: [[Copy of USER STORY TEMPLATES]]
---

# User story types

Four shapes of user story, ordered from a single task to a program-level goal. Start
from `.templates/user-story.md` to write one; this page says which shape to pick and
what each one contains.

## Simple

A single, sprint-sized task with one objective.

Fields: title, priority, estimate, sprint, user story, acceptance criteria. `sprint`
lives in frontmatter, set once a sprint plan schedules the story, empty while it's
still in the backlog.

```
As a [type of user], I want to [task], so I can [objective].

Given [initial context], when [action performed], then [expected outcome],
and [additional outcomes, if any].
```

Use this for a change small enough to finish in one sprint. It's the default shape:
reach for it first, and only move to a larger one below if the story doesn't fit in a
sprint.

## Epic

A feature too large for one sprint, broken into several simple stories.

Fields: epic name, one row per user story with its own acceptance criteria.

```
Epic: <name>
- Story 1: As a [type of user], I want to [task], so I can [objective].
  Given [initial context], when [action performed], then [expected outcome].
- Story 2: ...
```

Use this when a feature needs a roadmap across sprints or releases, and each row is
still a story you could start from `.templates/user-story.md` on its own.

## Thematic

A group of stories tied to one business goal (a theme), the highest strategic level in
this set.

Fields: theme, one row per story with priority, estimate, acceptance criteria, and
target release.

```
Theme: <name>
- Story 1: As a [type of user], I want to [task], so I can [objective].
  Priority: <level>. Estimate: <story points>.
  Given [initial context], when [action performed], then [expected outcome].
  Release: <sprint or version>.
```

Use this to plan a release around a goal, when several unrelated epics all serve the
same objective and need to land together.

## SAFe

A story written for a Scaled Agile Framework team, carrying program-level fields
alongside the story itself.

Fields: user story, description, hypothesis, nonfunctional requirements, acceptance
criteria, user business value, cost of delay, time criticality, job size, risk
reduction, and a Weighted Shortest Job First (WSJF) score.

```
As a [type of user], I want to [task], so I can [objective].

Description: <what the story is, in one or two sentences>
Hypothesis: <the measurable benefit this is expected to produce>
Nonfunctional requirements: <performance, security, or compliance constraints>
Acceptance criteria: Given [initial context], when [action performed],
  then [expected outcome].
User business value: <level or points>
Cost of delay: <how time-sensitive this is>
Time criticality: <how urgent this is>
Job size: <relative size>
Risk reduction: <risk this reduces, if any>
WSJF: <priority score>
```

Use this only on a Scaled Agile team that already scores stories with WSJF. On this
project, that's not the case, so default to Simple or Epic instead.

## Source

Synthesized from `raw/ideas/PRD-howto/Copy of USER STORY TEMPLATES.txt`, a Product
School template deck. That file is the original, unedited material; this page is the
version to read and cite going forward.
