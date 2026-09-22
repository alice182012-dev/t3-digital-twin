---
date_captured: 2026-09-23
type: idea
status: unexplored
source: "https://github.com/WorldFlowAI/everything-claude-code, https://x.com/affaan/status/2012378465664745795"
subsystem: AI tooling / Claude Code config
tags: [idea, claude-code, tooling]
related: []
---

# Adopt pieces of "everything-claude-code" into this project's Claude Code setup

## Idea

`everything-claude-code` is a public Claude Code plugin (agents, skills,
hooks, commands, rules, MCP configs) published alongside the two guide
clippings sitting next to this file. Evaluated it as a candidate to install
or cherry-pick from, on top of the pstack + gstack setup this project
already runs.

Guide:
[[The Longform Guide to Everything Claude Code]]
[[The Shorthand Guide to Everything Claude Code]]

## Why it might be worth it

The repo claims 10+ months of daily-use hardening. Two specific pieces
looked like they could close a real gap:

- A `PreToolUse` hook that blocks/nudges long-running Bash commands
  (`npm run dev`, `pytest`, `docker`, ...) toward `tmux`, so logs stay
  attachable instead of scrolling off. This project already has a memory
  rule (`feedback_long_running_local_ops`) asking for a time estimate before
  long commands, but that rule is only enforced by me remembering it, not by
  the harness.
- A `continuous-learning` Stop hook that auto-extracts reusable patterns
  from a session into `~/.claude/skills/learned/` without a manual trigger.

## Cost-benefit summary

| Repo component | Existing equivalent here | Verdict |
|---|---|---|
| `agents/*` (architect, planner, tdd-guide, code-reviewer, ...) | `pstack:architect`, `pstack:tdd`, `/code-review`, `/review` | Skip, yours is more mature and already wired to `poteto-mode` |
| `rules/*.md` | This project's `.claude/CLAUDE.md` (Apple style guide, Google dev style, code-review process) | Skip, already more detailed |
| `skills/verification-loop`, `skills/eval-harness` | gstack `/qa`, `/ship`, `/review` | Skip, theirs is a manual markdown checklist; yours is an actual pipeline |
| `commands/tdd.md`, `plan.md`, `refactor-clean.md` | `pstack:tdd`, `pstack:architect`, `pstack:no-comments` | Skip |
| `hooks/memory-persistence/*` | The harness's built-in auto-memory system | Skip, theirs is a cruder DIY version of what already exists natively |
| `mcp-configs/mcp-servers.json` | Already known (same list as the saved Shorthand Guide) | Skip |
| console.log/prettier/tsc auto-check hooks | N/A, this repo is Python/Airflow/Docker; the only JS/TS surface is `minio_custom/frontend` | Skip, cost of scoping outweighs benefit for one small frontend |
| Block-random-`.md`-creation hook | N/A | Bad fit as-is: hardcodes an allowlist that would block this vault's own `artifacts/logs/`, `artifacts/docs/claude-plan/`, `artifacts/docs/concepts/`, `artifacts/docs/blockers/` writes |
| `strategic-compact` (suggest `/compact` every 50 tool calls) | Manual `/compact`, automatic compaction already in place | Marginal, skip unless context limits become a recurring problem |
| `continuous-learning` Stop hook | The harness's auto-memory system, `pstack:recall`, `pstack:reflect` | Skip, running two competing persistence systems for the same job risks drift between them |
| tmux/long-running-command `PreToolUse` hook, retargeted at `docker`/`docker compose` on the remote host | `feedback_long_running_local_ops` memory rule (soft, not enforced) | The one piece with real marginal value, but small enough to write directly rather than pull in the whole plugin |

Net: nothing in the repo clears the bar of "materially better than what
pstack/gstack already give this project." Installing the plugin wholesale
would also reintroduce the exact MCP context-bloat problem the guide itself
warns about (20-30 MCPs configured, most projects only need 5-6 enabled).

## What's already covered

pstack owns implementation-time workflow (architect, TDD, review). gstack
owns the idea-to-shipped lifecycle (office-hours, plan reviews, `/qa`,
`/ship`). The harness's own auto-memory system covers session-to-session
persistence. Between the three, everything in this repo except the
docker/tmux hook is already handled, usually by a more capable version.

## Trigger to revisit

Only the one hook is worth building, and only if the remote-server
docker/Airflow workflow keeps causing long-running-command surprises (a
hung `docker compose up` with no attached logs, a build that silently ran
against the wrong context). If that happens two or three times, write a
`PreToolUse` hook scoped to `docker`/`docker compose` directly into
`.claude/settings.json` instead of pulling in the plugin, going through
`pstack:poteto-mode` since it's a real config change.

## Status history

- **2026-09-23, unexplored.** Full cost-benefit run against the current
  pstack + gstack setup; no adoption action taken. Captured here in case
  the docker/tmux hook trigger above fires later.
