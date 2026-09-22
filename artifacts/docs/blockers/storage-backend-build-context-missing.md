---
date_discovered: 2026-09-22
type: blocker
status: open
severity: P2
subsystem: storage-backend
related: ["[[storage-backend-django-layer]]"]
last_updated: 2026-09-22
---

# storage-backend and storage-frontend can't build

`compose.yml`'s `storage-backend` and `storage-frontend` services build from `./minio_custom/backend`
and `./minio_custom/frontend`, but that directory was deleted in commit `0a166f0` and never restored.
`docker compose up --build` cannot build either service as the repo stands. Full detail on what was
removed and why in [[storage-backend-django-layer]] and `TODOS.md`'s matching item.

## Status history

- **2026-09-22, open.** Found while writing [[storage-backend-django-layer]]. No decision made yet
  on restoring `minio_custom/` from commit `dd9f3e4`'s tree versus removing the dead service blocks
  from `compose.yml` and `README.md` to match reality.

Update `status` to `resolved` once `compose.yml` and `README.md` agree with whichever decision gets
made, and note which direction was chosen in a new dated bullet above.
