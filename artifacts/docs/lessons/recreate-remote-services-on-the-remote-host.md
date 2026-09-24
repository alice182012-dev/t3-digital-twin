---
date_captured: 2026-09-24
type: lesson
status: active
subsystem: docker-remote-host
source_blockers: []
tags: [lesson, docker, compose, remote-host]
related: ["[[2026-09-23]]", "[[graphhopper-backend]]"]
---

# Recreate remote services on the remote host

## Rule

To start, rebuild, or recreate a service, run `docker compose` on the remote host over SSH, and
add `--no-deps`. Use `docker --context remote-server compose` from the Mac only for read-only
commands such as `ps`, `logs`, and `exec`.

## Why

On 2026-09-24, `docker --context remote-server compose up -d --build flood-routing-frontend` ran
from the Mac. Compose expands relative bind-mount paths on the client, so `graphhopper` was
recreated with the source `/Users/maianhtran/.../grasshopper-routing/osm/hanoi-model-area.osm.pbf`,
a path that exists on neither machine's Docker host. The container failed to start. Compose also
recreated the dependencies of the named service, so `storage-postgres`, `graphhopper`, and
`floodmap-backend` were all recreated, and `graphhopper`, `floodmap-backend`, and
`flood-routing-frontend` stayed stopped in the `Created` state. Routing and the flood app were down
until I restarted them from the server.

`.claude/CLAUDE.md` says bind-mount paths resolve on the remote host under the `remote-server`
context. For `up` and `build` run from the Mac, the error message shows the opposite.

## How to apply

The rule is live whenever a task needs `up`, `build`, `restart`, or `--force-recreate` for a service
with a bind mount or a build context. From a PowerShell session on the server (SSH's default
shell, which rejects `&&`), run:

`cd C:\Users\TECOTEC\airflow_new; docker compose up -d --no-deps <service>`

Then run `docker --context remote-server ps` and confirm that every service the task touched is
`Up`, not `Created`. A build context is also read on the client, so a rebuild from the Mac sends the
Mac's files. Keep the checkout on the server at the same commit first.

## Source blockers

None. The incident was fixed in the same session and is recorded in [[2026-09-23]].

## Status history

- **2026-09-24, active.** Captured after a rebuild from the Mac took routing and the flood app
  offline.
