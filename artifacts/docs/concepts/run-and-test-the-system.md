---
date: 2026-10-27
type: concept
status: active
tags: [operations, docker, tests]
related: ["[[system-reference]]", "[[3di-simulation-orchestration]]"]
last_updated: 2026-10-27
---

# Run and test the system

This page covers the Docker host rules, the environment, the Airflow pools, the health checks, and the tests. For the first start, follow the quickstart in the [README](../../../README.md).

## Docker runs on the remote server

The stack runs on a remote Windows host, not on your machine. Your Docker client reaches it
through the `remote-server` context.

- For read-only commands such as `ps`, `logs`, and `exec`, use
  `docker --context remote-server compose` from your machine.
- To start, rebuild, or recreate a service, SSH to the host and run `docker compose` there with
  `--no-deps`. Compose resolves bind-mount paths and the build context on the client. A recreate
  from your machine mounts paths that do not exist on the host, and it also recreates the
  service's dependencies.

For the incident behind this rule, see
[`recreate-remote-services-on-the-remote-host.md`](../lessons/recreate-remote-services-on-the-remote-host.md).

## Configure the environment

1. Copy the example file in the repository root on the host.

   ```bash
   cp .env.example .env
   ```
2. Replace the placeholder values. `compose.yml` refuses to start without `MINIO_ROOT_USER`,
   `MINIO_ROOT_PASSWORD`, `POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY`, `TIMESCALE_PASSWORD`,
   `TOMORROW_API_KEY`, `THREEDI_API_KEY`, and `ORG_UUID`.
3. Set `THREEDI_API_PERSONAL_API_TOKEN`. `scripts/threedi_client.py` uses it to call the 3Di API.
4. Put the model inputs on the host. `flood_mapping_full` reads `data/mapping/inputs/gridadmin.h5`,
   `data/mapping/inputs/dem.tif`, and `data/mapping/inputs/toa-do-duong-hanoi.geojson`.
   GraphHopper reads `../grasshopper-routing/osm/hanoi-model-area.osm.pbf`.
5. Check that Compose resolves the file on the host.

   ```bash
   cd PROJECT_DIR; docker compose config --quiet
   ```

## Start or recreate a service

1. Get your committed changes onto the host. The host's SSH shell is PowerShell, so chain
   commands with `;`, not `&&`.

   ```bash
   cd PROJECT_DIR; git pull
   ```
2. Start or rebuild the service on the host. Replace `SERVICE` with a service name from
   `compose.yml`, such as `floodmap-backend`.

   ```bash
   cd PROJECT_DIR; docker compose up -d --build --no-deps SERVICE
   ```
3. Check that every service you touched is `Up`, not `Created` or `Exited`.

   ```bash
   docker --context remote-server compose ps
   ```

## Create the Airflow pools

Create the three pools once per Airflow database. The DAG files cannot create them. A task whose
pool does not exist stays unscheduled until the pool is created.

```bash
docker --context remote-server compose exec airflow-apiserver airflow pools set threedi_trigger 2 "Rain check and 3Di trigger"
docker --context remote-server compose exec airflow-apiserver airflow pools set depth_calc 1 "One depth calculation at a time"
docker --context remote-server compose exec airflow-apiserver airflow pools set routing_adapter 1 "Routing tasks of routing_adapter, one at a time"
```

## Create the first storage UI user

```bash
docker --context remote-server compose exec storage-backend python manage.py createsuperuser
```

Log in to `storage-frontend` on port 5173 with that user.

## Check that the stack answers

`floodmap-backend` publishes port 8010 on the host. Query it from your machine.

```bash
curl http://SERVER_ADDRESS:8010/health
curl http://SERVER_ADDRESS:8010/flood/runs
curl http://SERVER_ADDRESS:8010/flood/timesteps
```

Replace `SERVER_ADDRESS` with the host's address.

`/health` reports `ok`, plus the reachability of `graphhopper` and `postgis`. The Airflow UI on
port 8080 shows each `flood_mapping_full` run. The login comes from `_AIRFLOW_WWW_USER_USERNAME`
and `_AIRFLOW_WWW_USER_PASSWORD` in `.env`.

A depth or route test needs a point inside the model area. Outside it, the raster has no depth and
GraphHopper often finds no road. The area in EPSG:4326 is longitude 105.7015 to 105.7971 and
latitude 20.9754 to 21.0269.

## Run the tests

The pipeline tests use `unittest` and need the packages in `requirements.txt`.

```bash
python -m unittest discover -s test
```

Each backend test file under `floodmap/graphhopper-flood-road/backend/` names the database it
needs in its docstring. `test_server.py` runs against a throwaway PostGIS container and a stub
GraphHopper. The frontend tests use Jest.

```bash
cd floodmap/graphhopper-maps
npm install
npm test
```
