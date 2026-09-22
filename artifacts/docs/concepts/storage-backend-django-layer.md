---
date: 2026-09-22
type: concept
status: active
tags: [minio, storage-backend, broken]
related: ["[[minio-flood-extent-pipeline]]", "[[storage-backend-build-context-missing]]"]
last_updated: 2026-09-22
---

# Storage-backend (Django/MinIO UI): removed, but still wired into compose.yml

`compose.yml` still defines `storage-backend` and `storage-frontend` services, but the source
directories they build from do not exist in this repository. `docker compose up --build` cannot
build either service as the compose file stands on 2026-09-22.

## What's actually there

`compose.yml`'s `storage-backend` service builds from `./minio_custom/backend`
(`gunicorn config.wsgi:application`), and `storage-frontend` builds from `./minio_custom/frontend`.
Neither directory exists in this checkout. `git log --oneline --all -- minio_custom` shows why:
commit `dd9f3e4` (`init`) added the `minio_custom/` subproject, and commit `0a166f0`
("Update flood pipeline scripts, add 3Di client/tests, remove minio_custom, add SW architecture
doc") deleted it, as one part of a commit whose message is mostly about an unrelated 3Di client
change. `compose.yml` and `README.md` were not updated in that same commit, so both still describe
a service that can no longer build.

`README.md` line 6 still lists "`minio_custom`: MinIO plus Django/React storage UI" as part of the
stack, and its setup steps still instruct
`docker compose exec storage-backend python manage.py createsuperuser` (line 124).

## What it used to do

Before removal, `minio_custom/backend` was a Django REST app (`storage_api`), authenticating with
JWT (`storage_api/authentication.py`) and talking to MinIO through a `boto3` S3 client
(`storage_api/minio_client.py`, reading `settings.MINIO_ENDPOINT` /
`MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`). It had its own Postgres-backed models for roles,
visibility, and access groups (three migrations:
`0001_roles_visibility`, `0002_access_groups`, `0003_userprofile_userprofile_role_idx_and_more`),
a 200-line `serializers.py`, and an 867-line `views.py`. `minio_custom/frontend` was a Vite React
shell "for later screenshot-driven UI work" per its own README. The two together were meant to give
a human operator a UI over the raw MinIO buckets: browse, upload, and manage access, separate from
the flood pipeline's own automated bucket use.

## What still depends on it in compose.yml

`storage-backend` still declares `depends_on: storage-postgres` (`condition: service_healthy`) and
reads `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` from the same `storage-postgres` instance
that [[graphhopper-backend]]'s `flood_areas.py`, `flood_extent_runs.py`, and `db.py` also connect
to (default database name `minio_custom`). `storage-postgres` itself is unaffected: it is PostGIS,
used directly by the GraphHopper backend regardless of whether `storage-backend` ever builds.

## Open items

- Decide whether `storage-backend`/`storage-frontend` should be restored (from `dd9f3e4`'s tree, if
  wanted), or removed from `compose.yml` and `README.md` to match what commit `0a166f0` actually
  did (live status in [[storage-backend-build-context-missing]]). Either way, `compose.yml` and
  `README.md` currently describe a stack that cannot fully build,
  which is worth its own TODOS.md item.
- If removed for good, check whether anything outside `minio_custom/` (scripts, other services)
  still assumes a human-facing bucket browser exists, versus the flood pipeline's own direct
  `boto3` use (`scripts/mapping/upload_minio.py`, `scripts/flood_extent/publish.py`), which does
  not depend on this service at all.
