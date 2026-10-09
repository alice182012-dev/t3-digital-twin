---
date_drafted: 2026-09-29
type: user-story
us_id: "US-038"
story_label: "7"
epic: "[[EP-07-carried-over-backlog]]"
status: Done
priority: P3
estimate: S
sprint: 3
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Fix the documentation and config drift found by the README rewrite"
---

# US-038 Fix the documentation and config drift found by the README rewrite

As a new teammate, I want `.env.example`, the vault links, and the concept pages to match the code, so a fresh
checkout starts and its docs do not contradict the DAG.
Given the drift in [[BL-015-documentation-and-config-drift-after-graphhopper|documentation-and-config-drift-after-graphhopper]], when this is done, then `.env.example`
lists the variables `compose.yml` reads (with `THREEDI_API_PERSONAL_API_TOKEN`) and none it does not, no
`[[SW Architecture]]` link or comment is left outside `artifacts/raw/`, the 3Di orchestration concept page states
the cron `*/15` schedule with `max_active_runs=2` once, and `PINNED_COMMIT.md` lists only files that exist.
Priority: P3. Status: Done. Estimate: S. Sprint: 3 (found 2026-09-30, fixed by a subagent under rule 11 in `1792d37`). Dependencies: None.
Blocker tracking: [[BL-015-documentation-and-config-drift-after-graphhopper|documentation-and-config-drift-after-graphhopper]]
Evidence: ![[us-038-drift-check-output.png|700]]
Details:
1. What: `.env.example`, the `[[SW Architecture]]` links, the 3Di orchestration concept page, and `PINNED_COMMIT.md` now match the code.
2. How: a subagent fixed them in `1792d37` under rule 11. The script `evidence/us-038-drift-check.sh` then compared `.env.example` with the variables `compose.yml` reads, searched the main tree for `[[SW Architecture]]`, counted `*/15` and `max_active_runs=2` on the orchestration page, and looked up every file `PINNED_COMMIT.md` names.
3. Why: a fresh checkout should start from `.env.example`, and the docs should not contradict the DAG.
4. Effect: all four checks pass, run on the Mac at 2026-09-30 16:16 (`gods-macbook.local`). The criterion "lists the variables `compose.yml` reads" is read as: every required variable (`${NAME:?...}`) is listed, and variables with a default in `compose.yml` may be left out. Sixteen optional variables are left out on purpose. The search skips `.claude/worktrees`, which hold stale copies of older branches.
