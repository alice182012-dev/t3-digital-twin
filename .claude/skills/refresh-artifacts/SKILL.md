---
name: refresh-artifacts
description: >
  Re-reads the artifacts/ Obsidian vault in this repo (t3-digital-twin) to refresh Claude's
  understanding of current project state: active plans, open blockers, recent logs, draft or
  in-progress PRDs, the current sprint plan, and captured lessons. Use this whenever the user asks
  to "catch up on the project", "refresh context", "what's the current state", "resume work",
  "what's blocked", "what's in progress", or starts a new session on this project after a gap.
  Also use it proactively at the start of a session on this repo if the vault hasn't been read yet
  this session, since Home.md and TODOS.md are the source of truth for what's actually active, not
  memory or a guess from file timestamps. Does not blindly read every file in the vault: the vault
  grows over time, so this skill follows Home.md's own dataview queries to pick out what's
  load-bearing (active, open, draft, recent) and skips what's settled (shipped, resolved, done),
  reference-only, or read-only source material.
---

# Refresh artifacts

The vault at `artifacts/` is this project's actual source of truth for what's happening: what's
being built, what's blocked, what's been decided, and why. Reading it fresh beats trusting memory
or a prior summary, since the vault gets updated mid-session by this session and by the user
directly, and Home.md's dataview queries already encode which files matter right now versus which
are settled history.

## Why selective, not exhaustive

The vault is designed to grow. `artifacts/raw/` holds primary source material that can be large,
`logs/` accumulates one file per day, and `docs/concepts/` accumulates one page per subsystem.
Reading everything defeats the vault's own purpose: Home.md's dataview queries already filter each
category down to what's active, and this skill mirrors that filtering by hand (approximating each
query with a directory listing plus a frontmatter check), rather than re-reading history that's
already settled.

## Steps

1. **Read `artifacts/Home.md` in full.** It's the vault index and states its own conventions:
   frontmatter fields, file-type rules, and what belongs where. Read it every time, even if it
   seems familiar. It changes as the vault's own conventions evolve (see its `related` links and
   Conventions section for the current rules), and following stale conventions produces files that
   don't match what's actually there anymore.

2. **Read `artifacts/TODOS.md` in full.** It's the project backlog, kept in prose with inline
   `Status:: active` fields rather than as a Dataview-only table, so it needs a full read rather
   than a query approximation.

3. **For each of Home.md's dataview-backed sections, approximate the query and read only the
   matches.** Home.md's queries filter by `status`; a plain directory listing doesn't apply that
   filter, so check each file's frontmatter before deciding whether to open it in full. In order:

   - **Blockers** (`docs/blockers/`): read in full any page with `status: open` or
     `status: monitoring`. Skip the body of a `resolved` or `wont-fix` blocker; note its title and
     status only, since a resolved blocker is history, not something the current session needs to
     act on. Note: `resolved`/`wont-fix` are lowercase and the field is `status`, not
     `date_closed` — grep frontmatter directly rather than assuming.
   - **Active plans** (`docs/claude-plan/`): read in full any page with `status: active`. Skip
     anything else in that folder.
   - **Recent logs** (`logs/`): read the two or three most recent dated files in full (sort by
     filename, which is `YYYY-MM-DD.md`). Skip older logs unless a blocker, plan, or PRD you're
     reading directly references one by date, in which case follow that specific link.
   - **PRDs** (`docs/prds/`): read in full any page with `status: draft`, `approved`, or
     `in-progress`. Skip the body of a `shipped` or `abandoned` PRD; note its title only.
   - **User stories and sprint plans** (`docs/user-stories/`): find the sprint-plan file with the
     highest `plan_number` in its frontmatter (there may be more than one:
     `sprint-plan.md`, `sprint-plan-2.md`, and so on — higher `plan_number` is the current planning
     pass) and read it in full. Then read, in full, only the epic or story files it links to whose
     own `status` isn't `done`. Skip a completed story's body; note its title only.
   - **Concepts** (`docs/concepts/`): list titles and `last_updated` dates only, don't read bodies
     by default. Concepts are standing reference, not recent activity, so they don't belong in an
     initial refresh. Read a specific concept page in full only when something else you just read
     (an active plan, an open blocker, a draft PRD) links to it and the task at hand needs that
     subsystem's detail.
   - **Lessons** (`docs/lessons/`): read all of them in full, regardless of `status`. They're
     short, checkable rules by design (the template caps them at three short sections), so the
     cost of reading all of them is low and the cost of missing one (repeating a mistake it exists
     to prevent) is exactly the failure mode this category exists to avoid.

4. **Skip `artifacts/raw/` bodies by default.** It's read-only source material and can be large
   (architecture docs, mockups, research). List what's there (`ls artifacts/raw/`,
   `ls artifacts/raw/ideas/`) so you know it exists, but only read a specific file in full when
   something else you're reading cites it directly and the current task needs that citation
   checked.

5. **Skip `artifacts/designs/` and `artifacts/.obsidian/` by default.** List `designs/` titles only
   (Home.md's own query does the same); `.obsidian/` is Obsidian's own app configuration, never
   relevant to a content refresh.

## Reporting back

End with a short status summary, not a transcript of everything read. Cover, in a few sentences
each: what's actively in progress (from Active plans and in-progress PRDs), what's blocked (from
open or monitoring blockers, one line each), what the most recent log entry actually accomplished,
and what's drafted but not yet approved (from draft PRDs and their sprint plan, if any). A wall of
restated file contents is not a refresh; the point is to load the state into context, not to prove
every file was opened.

If the user's actual request is more specific than "catch me up" (for example, "what's blocking
the frontend depth features"), let that request narrow which of the steps above matter most, but
still do step 1 and step 2 first: Home.md and TODOS.md are cheap to read and everything else is
found through them.
