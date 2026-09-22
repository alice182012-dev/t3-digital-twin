---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: architecture-backend
source_blockers: []
tags: [lesson, prd]
related: ["[[flood-routing-mockup-frontend-gap]]", "[[t3-digital-twin-architecture-gaps]]"]
---

# After a scope change, check every document that cross-references the one that changed

## Rule

When editing a document that another document's Dependencies section names by link, open the
linking document too and check whether its assumption still holds. Fixing the edited document
alone can leave a second document silently wrong.

## Why

`flood-routing-mockup-frontend-gap.md`'s Dependencies section named
`t3-digital-twin-architecture-gaps.md` as the PRD that would build `GET /flood/points`,
`GET /flood/forecast`, and `GET /flood/route/forecast`. When the user marked the citizen-endpoint
bundle "no need" in the architecture PRD, all three of those endpoints were gone, but the frontend
PRD still said its goals were "resolved" against them. This was caught by re-opening the frontend
PRD after the architecture PRD's edit, not automatically. Had the frontend PRD not been checked,
its Dependencies section would have kept citing endpoints that no longer existed anywhere in the
backlog.

## How to apply

Before considering a scope-changing edit finished, grep the vault for `[[wikilinks]]` to the file
just edited (`grep -rl '\[\[filename\]\]' artifacts/docs/`), open each hit, and check whether the
specific claim it makes about the edited file (an endpoint name, a table name, a decision) still
holds. This is the vault-level version of propagating a change through one document's own
sections: the same discipline, one level up, across files instead of within one.

## Source blockers

- None. Surfaced from the same-session cross-check between `flood-routing-mockup-frontend-gap.md`
  and `t3-digital-twin-architecture-gaps.md`.

## Status history

- **2026-09-23, active.** Captured after the architecture PRD's citizen-endpoint descoping broke
  an assumption in the frontend PRD's Dependencies section, caught by re-opening it.
