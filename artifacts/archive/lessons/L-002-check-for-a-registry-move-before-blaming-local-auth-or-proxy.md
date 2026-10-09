---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: docker-build
source_blockers: []
tags: [lesson, docker, registry, minio]
related: []
---

# Check for a registry move before blaming local auth or proxy on a Docker Hub pull denial

## Rule

When a `docker pull` of a known-public image returns "pull access denied ... may require 'docker
login'", test a different public image from the same registry before assuming the problem is local
(auth, proxy, Registry Access Management). If the other image pulls fine, the specific image likely
moved off Docker Hub or restricted anonymous pulls; check the vendor's current recommended registry.

## Why

`minio/minio` and `minio/mc` failed to pull with "pull access denied ... repository does not exist
or may require 'docker login'" right after a Docker purge, which looked exactly like a local
Docker Desktop proxy or Registry Access Management problem (the daemon was in fact routing through
`http.docker.internal:3128` / `hubproxy.docker.internal`). `docker logout` and retrying didn't fix
it. Pulling `alpine` and `postgres` from the same Docker Hub worked immediately, isolating the
problem to those two specific images. MinIO restricted anonymous Docker Hub pulls of `minio/minio`
in 2024 as part of a licensing change; `quay.io/minio/minio` and `quay.io/minio/mc` still allow
anonymous pulls and worked without any local configuration change.

## How to apply

On any "access denied" or "repository does not exist" pull error for an image that's supposed to be
public: pull a different, unrelated public image from the same registry as a control test before
touching local proxy settings, Docker Desktop sign-in state, or Registry Access Management. A
control-test failure means it's local; a control-test success narrows it to that one image or
namespace, which usually means a vendor-side registry or licensing change, not a local
misconfiguration.

## Source blockers

- None. Surfaced live during the airflow_new Docker stack rebuild on 2026-09-23.

## Status history

- **2026-09-23, active.** Captured after `minio/minio`'s Docker Hub pull denial was initially
  misdiagnosed as a Docker Desktop proxy/RAM issue; resolved by switching `compose.yml`'s `minio`
  and `minio-init` services to `quay.io`.
