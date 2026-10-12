# Analysis service

The analysis service runs the analysis application in its own container (US-109).
It builds from this folder with its own `Dockerfile` and `requirements.txt`, so it adds nothing to the Airflow image.

## Endpoint

`GET /health` returns the newest `run_ts` that has all four core outputs in `flood_run_output`, for example `{"run_ts": "20261011T001500"}`.
The four outputs are the values of `Output` in `scripts/database/run_output.py`.
When no run has all four, the response is `{"run_ts": null}`.
When the database refuses the connection, the response has status 503 and an `error` field.

## Environment variables

The service in `compose.yml` sets these variables and no others.
It does not read `.env` as a whole, so the 3Di, Tomorrow.io, and MinIO keys are not in its environment.

- `HOST` and `PORT` set the listening address. The defaults are `127.0.0.1` and `8020`, and the image sets `HOST` to `0.0.0.0`.
- `POSTGRES_HOST`, `POSTGRES_PORT`, and `POSTGRES_DB` locate `storage-postgres`.
- `ANALYSIS_READER_USER` and `ANALYSIS_READER_PASSWORD` are the role that `GET /health` reads with.
- `ANALYSIS_OWNER_USER` and `ANALYSIS_OWNER_PASSWORD` are the role that owns schema `analysis`, the only place the service writes.
- `TIMESCALE_HOST`, `TIMESCALE_PORT`, and `TIMESCALE_DB` locate `timescaledb`.
- `ANALYSIS_TIMESCALE_READER_USER` and `ANALYSIS_TIMESCALE_READER_PASSWORD` are the role that reads `timescaledb`.

Compose refuses to start when one of the three passwords is missing from `.env`.
`ANALYSIS_PORT` in `.env` sets the host port, which is bound to `127.0.0.1` only.

## Roles

Each role has its own script in `scripts/database/`.
Each script connects as the writer role, refuses to run without the role's password, and changes nothing on a second run.

- `create_routing_reader_role.py analysis_reader` makes `analysis_reader` in `storage-postgres`. The role can read the tables listed for it under "Reader roles" in `artifacts/docs/concepts/core-output-contract.md`.
- `create_analysis_schema.py` makes `analysis_owner` and schema `analysis` in `storage-postgres`. The role owns the schema and holds no right on schema `public` or its tables.
- `create_timescale_reader_role.py` makes `analysis_timescale_reader` in `timescaledb`. The role can read `depth_history` and `history_moment` and nothing else in schema `public`.

## Tests

Run the service tests from the repo root:

```bash
python3 -m pytest analysis-service/test
```

`test_health_db.py` runs the `GET /health` query against a real PostgreSQL in `FLOOD_TEST_DSN` and skips without it.
The role scripts have their tests next to them. Run them from `scripts/database/`:

```bash
python3 -m pytest test_create_analysis_schema.py test_create_timescale_reader_role.py
```

Their live tests read `FLOOD_TEST_DSN` and `FLOOD_TEST_TIMESCALE_DSN`, connect as a superuser, and skip without them.
`test/test_analysis_service_compose.py` checks the service's variable list in `compose.yml`.
