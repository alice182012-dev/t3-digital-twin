---
date_drafted: 2026-10-10
type: user-story
us_id: "US-110"
title: "Decide whether pipeline tables leave the public schema"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Done
kind: spike
priority: P3
estimate: S
sprint: 14
subsystem: storage, core-output
source_ideas: []
related: ["[[core-output-contract]]", "[[storage-backend-django-layer]]"]
tags: [user-story, spike]
---

# US-110 Decide whether pipeline tables leave the public schema

As a developer, I want to know whether the pipeline tables should leave schema `public`, so Django migrations and the pipeline DDL scripts stop sharing one schema.

**Question.**
What does it cost to move the pipeline tables into their own schema in `minio_custom`, and what breaks if they stay?

**Timebox.**
Half a sprint, on a copy of the database in `marie-curie/`.

The spike lists every table in `public` by owner (Django migrations or `scripts/database/`).
It then finds what a move changes: the grants in `create_routing_reader_role.py` (which name `public`), the queries in `floodmap/graphhopper-flood-road/backend/` and `scripts/` that do not qualify a schema, `test_core_contract.py`, and the connection `search_path`.
It also tests whether `python manage.py migrate` ever touches a pipeline table.

Given the spike on a copy of the server database, when it ends, then the story holds the table list by owner, the list of files a move changes, and a decision `D-nnn` that says move now, move later with a trigger, or stay.

Dependencies: None.

## Status history

- **2026-10-10, draft.** Ready: the question is stated, it has an estimate, and the answer is a decision.
- **2026-10-12, Sprint 13.** Picked at Sprint 13 planning at S (2 points). It has no dependency.
- **2026-10-12, Ready.** Left Sprint 13 to make room for [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]], because it has the lowest priority of the picks (P3). `sprint` is cleared and the story returns to the backlog.

- **2026-10-12, Ready.** Picked for the sprint at the product owner's request. It is a spike, so it ends with an answer and a `D-nnn` decision, and it works in `marie-curie/`. Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]].
- **2026-10-13, Reviewed.** The answer is in the details and in [[decision-log|D-049]]: stay in `public`, and move later with a trigger. The spike ran on read-only queries against the server database and not on a copy, because it changed nothing. The owner has not accepted it.
- **2026-10-13, Done.** The product owner accepted the answer and [[decision-log|D-049]] on the written results of details items 1 to 5.

## Evidence and details

**Evidence:** the table list in details item 1 and the scratch report `marie-curie/us110/code_scan.md` (not tracked by git).

**Details:**

1. `public` of `minio_custom` holds 30 tables on 2026-10-13, and the role `minio_custom` owns all of them.
   - 14 belong to Django: `auth_group`, `auth_group_permissions`, `auth_permission`, `auth_user`, `auth_user_groups`, `auth_user_user_permissions`, `django_admin_log`, `django_content_type`, `django_migrations`, `django_session`, `storage_api_accessgroup`, `storage_api_accessgroup_users`, `storage_api_userprofile`, and `storage_api_visibilitygrant`.
   - 15 belong to the pipeline: `demo_pin`, `edge_depth`, `edge_depth_run`, `flood_depth_raster_tile`, `flood_extent_polygon`, `flood_extent_step`, `flood_run_output`, `flood_segment_metrics`, `forecast_mode`, `graph_edge`, `graph_edge_export`, and four that [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] deletes: `road_segment`, `flood_road_values`, `flood_road_file`, and `flood_road_values_shadow`.
   - 1 belongs to PostGIS: `spatial_ref_sys`.
   The schema `tiger` holds the PostGIS geocoder tables, and the schema `analysis` (owned by `analysis_owner`, with the role-level `search_path` `analysis, public`) is the precedent of a separate schema ([[US-109-run-an-analysis-service-in-its-own-container|US-109]]).
2. `python manage.py migrate --plan` in `storage-backend` plans no operation. The 9 models have no `db_table` that names a pipeline table, no `managed = False`, and no raw SQL, and no migration refers to a pipeline table. So `migrate` never touches one, and nothing breaks if the tables stay.
3. A move changes about 7 files and adds one script. `scripts/database/roles.py` (the grants name `public`), `scripts/database/test_create_routing_reader_role.py` (22 literal statements), `floodmap/graphhopper-flood-road/backend/test_reader_role.py` (3 literals), `test_backend_reads_contract_tables.py` (the `public.` stripping), `scripts/testdata/run_db_tests.py`, the Django `settings.py` (an `OPTIONS` entry with `search_path=public`), and the contract page. The one-time script runs `CREATE SCHEMA`, `ALTER TABLE ... SET SCHEMA` for the 11 tables that remain after US-123, and `ALTER ROLE ... SET search_path` for the writer and two readers.
   About 200 unqualified table references in about 70 files stay as they are, so the move does not qualify any query. 11 test modules already run `SET search_path TO <scratch>, public`, and the Java router never opens a database connection.
4. The three risks of a move. First, Django and the pipeline writer share the role `minio_custom` (`compose.yml`), so a role-level `search_path` of `pipeline, public` would make `migrate` create Django tables in `pipeline`. Second, `to_regclass('forecast_mode')` and `to_regclass('demo_pin')` (`flood_mode.py`, `standing_flood.py`, `demo_pin.py`) return NULL when the schema is not on the path, and a caller can then treat the table as absent. Third, every reader needs `USAGE` on the schema, or every route request fails, and `ALTER TABLE ... SET SCHEMA` takes `ACCESS EXCLUSIVE` locks, so it must not overlap a run of `flood_mapping_full`.
5. Found on the way: `flood_road_values_shadow` (8,444 rows, 8.8 MB) is a pipeline table that US-123 does not list and that no code refers to. It joins the drop list of US-123.

