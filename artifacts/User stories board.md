---
type: reference
status: active
tags: [user-story, dataview]
related: ["[[Home]]"]
---

# User stories board

Every story, one row each, read from the frontmatter of the story files in `docs/stories/`. A story file is the single source for its sprint, priority, estimate, and status, so this page needs no edits when a story changes. To move a story to another sprint, change `sprint` in that story's frontmatter.

## All stories

```dataview
TABLE title AS "Story", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE type = "user-story"
SORT sprint ASC, priority ASC, file.name ASC
```

## Open stories

```dataview
TABLE title AS "Story", sprint AS "Sprint", priority AS "Priority", status AS "Status"
FROM "docs/stories"
WHERE type = "user-story" AND status != "Done" AND status != "Superseded"
SORT sprint ASC, priority ASC
```

## Count by status

```dataview
TABLE length(rows) AS "Stories"
FROM "docs/stories"
WHERE type = "user-story"
GROUP BY status
```

## Epics

```dataview
TABLE us_ids AS "Stories", status AS "Status", subsystem AS "Subsystem"
FROM "docs/epics"
SORT file.name ASC
```
