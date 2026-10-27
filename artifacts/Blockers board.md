---
type: reference
status: active
tags: [blocker, dataview]
related: ["[[Home]]", "[[User stories board]]"]
---
# Blockers board

Every blocker, one row each, read from the frontmatter of the pages in `docs/blockers/`. Each blocker
page is the single source for its status, severity, approach counts, and dates, so this page needs no
edits when a blocker changes. Update the blocker page instead.

This page uses `dataviewjs`. Turn on **Enable JavaScript Queries** in Settings > Community plugins
> Dataview, or the code blocks show as plain text.

## Unresolved blockers

Blockers with `status` set to `open` or `monitoring`, most severe first, then oldest first.

```dataviewjs
const rows = dv.pages('"docs/blockers"')
	.where(p => p.type === "blocker" && (p.status === "open" || p.status === "monitoring"))
	.sort(p => p.date_open, "asc")
	.sort(p => p.severity, "asc");

const today = dv.date("today");
dv.table(
	["Blocker", "Priority", "Status", "Subsystem", "Tried", "Remaining", "Opened", "Days open"],
	rows.map(p => [
		p.file.link,
		p.severity,
		p.status,
		p.subsystem,
		p.approaches_tried,
		p.approaches_remaining,
		p.date_open,
		Math.floor(today.diff(dv.date(p.date_open), "days").days),
	])
);
```

## Resolved blockers

Blockers with `status` set to `resolved` or `wont-fix`, most recently closed first.

```dataviewjs
const rows = dv.pages('"docs/blockers"')
	.where(p => p.type === "blocker" && (p.status === "resolved" || p.status === "wont-fix"))
	.sort(p => p.date_closed, "desc");

dv.table(
	["Blocker", "Priority", "Status", "Subsystem", "Tried", "Opened", "Closed", "Days to close"],
	rows.map(p => [
		p.file.link,
		p.severity,
		p.status,
		p.subsystem,
		p.approaches_tried,
		p.date_open,
		p.date_closed,
		Math.floor(dv.date(p.date_closed).diff(dv.date(p.date_open), "days").days),
	])
);
```

## Reading the columns

- **Priority** is the `severity` field, where P1 is more urgent than P2.
- **Status** is `open` (no fix confirmed), `monitoring` (a fix is attempted, not yet confirmed),
  `resolved`, or `wont-fix`.
- **Tried** is `approaches_tried`, and **Remaining** is `approaches_remaining`. The `### Approach N`
  sections in each blocker page describe each attempt.
- **Days open** counts from `date_open` to today. **Days to close** counts from `date_open` to
  `date_closed`.
