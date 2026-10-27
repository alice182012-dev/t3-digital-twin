---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: docker-build
source_blockers: []
tags: [lesson, docker, background-process, windows]
related: []
---

# Confirm a background process is dead before retrying in parallel

## Rule

Before relaunching a command you believe stalled or died, confirm it actually exited by checking
its effect (output file still growing, containers appearing, the resource it was creating), not by
`pgrep -f "<command line>"` alone on Windows/Git Bash.

## Why

A `docker compose up -d --build` run was assumed dead because `pgrep -f "docker compose -f
compose.yml up"` returned no match after a period of silence. `ps aux` on this Windows/Git Bash
setup showed only the bare `docker` binary path with no arguments, so the `-f` pattern never had a
command line to match against, even though the process was alive and still downloading layers. A
second `docker compose up -d --build` was launched in parallel on the same project. Both eventually
finished building the same images, then raced each other on the final `up` step: one created
`airflow_new-minio-1`, the other hit `Error response from daemon: Conflict... container name ...
already in use`, and several containers were left stuck in `Created` (never started) state. A third,
clean `docker compose up -d` was needed to reconcile the mess.

## How to apply

When a long-running build or deploy command looks stalled: check whether its output file is still
growing (`ls -la` the log, compare timestamps across a wait), or whether the resource it's building
toward exists yet, before concluding it's dead. If `pgrep -f` is the only signal available, treat a
negative result as inconclusive on this environment rather than confirmed, and check `ps aux` output
format first to see whether it even carries arguments. Never launch a second instance of the same
mutating command (build, migration, `up`, deploy) against the same target while unsure whether the
first is still running — a race on shared names/resources is a likely outcome, not an edge case.

## Source blockers

- None. Surfaced live during the airflow_new Docker stack rebuild on 2026-09-23.

## Status history

- **2026-09-23, active.** Captured after a duplicate `docker compose up --build` caused a container
  name conflict and stuck `Created`-state containers, traced back to a false-negative `pgrep -f`
  check.
