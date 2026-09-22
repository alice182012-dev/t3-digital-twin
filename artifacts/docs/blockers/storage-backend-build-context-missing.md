---
date_open: 2026-09-22
date_closed: 
type: blocker
status: open
severity: P2
subsystem: storage-backend
approaches_tried: 0
approaches_remaining: 2
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

None yet. Found while writing [[storage-backend-django-layer]]; no attempt made to fix it.

## Decision and explanation

Pending. Two options, neither attempted:

- **Restore** `minio_custom/` from commit `dd9f3e4`'s tree (the last commit before removal).
- **Remove** the dead `storage-backend`/`storage-frontend` blocks from `compose.yml` and the
  matching setup steps from `README.md`, so the repo matches what commit `0a166f0` actually did.

The removal commit's own message is mostly about an unrelated 3Di client change; nothing in it
explains whether dropping `minio_custom` was deliberate scope-narrowing or incidental, so the
decision needs the user's input, not a guess from the commit history alone.

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

Update `status` to `resolved` once `compose.yml` and `README.md` agree with whichever decision gets
made; set `date_closed` at that point. Note which direction was chosen in a new dated bullet above.
