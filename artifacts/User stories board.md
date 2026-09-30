---
type: reference
status: active
tags: [user-story, dataview]
related: ["[[sprint-plan]]", "[[Home]]"]
---

# User stories board

Every story, one row each, read from the sprint tables in [[sprint-plan]]. That file is the single
source for sprint, priority, and status, so this page needs no edits when a story changes. Story
bodies live in the epic files under `docs/user-stories/`.

This page uses `dataviewjs`. Turn on **Enable JavaScript Queries** in Settings > Community plugins
> Dataview, or the code blocks show as plain text.

## All stories

```dataviewjs
const plan = dv.page("docs/user-stories/sprint-plan");
const text = await dv.io.load(plan.file.path);

const stories = [];
let sprint = null;
let header = null;
for (const line of text.split("\n")) {
	const heading = line.match(/^## Sprint (\d+)/);
	if (heading) { sprint = Number(heading[1]); header = null; continue; }
	if (/^## /.test(line)) { sprint = null; header = null; continue; }
	if (sprint === null || !line.startsWith("|")) continue;

	const cells = line.split(/(?<!\\)\|/).slice(1, -1).map(c => c.trim());
	if (cells.includes("Priority")) { header = cells; continue; }
	if (!header || /^-+$/.test(cells[0])) continue;

	const row = Object.fromEntries(header.map((name, i) => [name, cells[i]]));
	const epicName = (row["Epic"] || "").match(/\[\[([^\]|]+)/)?.[1];
	const epicPage = epicName ? dv.page(epicName) : null;
	stories.push({
		sprint,
		item: row["Item"],
		priority: row["Priority"],
		story: row["Story"],
		estimate: row["Estimate"],
		epic: epicPage ? epicPage.file.link : row["Epic"],
		status: row["Status"],
	});
}

stories.sort((a, b) => a.sprint - b.sprint || a.priority.localeCompare(b.priority));
dv.table(
	["Item", "Sprint", "Priority", "Story", "Estimate", "Epic", "Status"],
	stories.map(s => [s.item, s.sprint, s.priority, s.story, s.estimate, s.epic, s.status])
);
```

## Count by status

```dataviewjs
const plan = dv.page("docs/user-stories/sprint-plan");
const text = await dv.io.load(plan.file.path);

const counts = {};
let sprint = null;
let statusColumn = -1;
for (const line of text.split("\n")) {
	const heading = line.match(/^## Sprint (\d+)/);
	if (heading) { sprint = Number(heading[1]); statusColumn = -1; continue; }
	if (/^## /.test(line)) { sprint = null; continue; }
	if (sprint === null || !line.startsWith("|")) continue;

	const cells = line.split(/(?<!\\)\|/).slice(1, -1).map(c => c.trim());
	if (cells.includes("Priority")) { statusColumn = cells.indexOf("Status"); continue; }
	if (statusColumn < 0 || /^-+$/.test(cells[0])) continue;

	const status = cells[statusColumn];
	counts[status] = (counts[status] || 0) + 1;
}

dv.table(["Status", "Stories"], Object.entries(counts).sort((a, b) => b[1] - a[1]));
```

## Story files

One row per epic or single-story file, from frontmatter.

```dataview
TABLE us_ids AS "IDs", status AS "File status", subsystem AS "Subsystem", sprint AS "Sprint", date_drafted AS "Drafted"
FROM "docs/user-stories"
WHERE type = "user-story"
SORT subsystem ASC, date_drafted DESC
```
