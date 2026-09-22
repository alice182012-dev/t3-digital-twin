---
date_open: 2026-09-22
date_closed: 2026-09-22
type: blocker
status: resolved
severity: P2
subsystem: storage-backend
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, storage-backend]
related: ["[[storage-backend-django-layer]]"]
last_updated: 2026-09-22
---

# storage-backend and storage-frontend can't build

## Description

`compose.yml`'s `storage-backend` and `storage-frontend` services build from
`./minio_custom/backend` and `./minio_custom/frontend`, but that directory was deleted in commit
`0a166f0` ("Update flood pipeline scripts, add 3Di client/tests, remove minio_custom, add SW
architecture doc") and never restored. `docker compose up --build` cannot build either service as
the repo stands.

## Why this matters

`README.md` still lists this Django/React storage UI as part of the stack and still instructs
running `docker compose exec storage-backend python manage.py createsuperuser` as part of first-run
setup, so a new contributor following the README hits a build failure on the documented path.

## Approaches tried

- **Restore.** `git checkout dd9f3e4 -- minio_custom/` brought back the full directory (Django
  backend, React frontend, both Dockerfiles) exactly as it stood in the last commit before
  removal. `docker compose -f compose.yml config --services` now resolves `storage-backend` and
  `storage-frontend` without error, confirming both build contexts exist again. Worked, no further
  attempts needed.

## Decision and explanation

Restored, per the user's direction. `minio_custom/` is back at the repo root, matching the path
`compose.yml` already expected. The removal commit (`0a166f0`) never explained why `minio_custom`
was dropped, and its message is mostly about an unrelated 3Di client change, so restoring rather
than guessing that the drop was deliberate was the safer read.

## Concerns

`storage-backend` still declares `depends_on: storage-postgres` and reads
`POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` from the same `storage-postgres` instance that
[[graphhopper-backend]]'s `flood_areas.py`, `flood_extent_runs.py`, and `db.py` also connect to. If
the decision is "remove," double-check nothing else assumes `storage-postgres` stays up only
because `storage-backend` depends on it.

## Related topics

- [[storage-backend-django-layer]]. What the removed Django app did, in full.
- `TODOS.md`'s "compose.yml's storage-backend/storage-frontend build from a removed directory" item

## Status history

- **2026-09-22, open.** Found while writing [[storage-backend-django-layer]]. No decision made yet.
- **2026-09-22, resolved.** Restored `minio_custom/` from `dd9f3e4`. `compose.yml`'s build contexts
  for `storage-backend` and `storage-frontend` resolve again; no changes needed to `README.md`, since
  its documented setup steps now match the restored tree.
