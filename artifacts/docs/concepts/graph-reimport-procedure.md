---
date: 2026-10-05
type: concept
status: active
tags: [graphhopper, reimport, edge-depth-table, graph-hash, operations]
related: ["[[edge-depth-table-format]]", "[[edge-depth-table-publish]]", "[[edge-depth-table-airflow-task]]", "[[graph-reimport-procedure-and-stale-table-check]]", "[[graphhopper-backend]]", "[[EP-08-edge-depth-table|edge-depth-table-stories]]", "[[lessons#L-010|recreate-remote-services-on-the-remote-host]]"]
last_updated: 2026-10-12
---

# Graph re-import procedure

What to do after the GraphHopper graph is re-imported, so the edge depth table and the graph never drift apart unnoticed. It is the operator page of `US-044`.

## Why a re-import matters

GraphHopper numbers its edges when it imports an OSM file, and the numbers change on every import. The edge depth table stores one depth per edge id and holds no ids of its own, so a table built for the old graph puts depth on the wrong roads of the new one. Each table carries the hash of the graph it was built for (`graphHash` in its header, [[edge-depth-table-format]]). A reader that has loaded the new graph must refuse a table with another hash.

Four places hold that hash, and a re-import has to bring all of them to the new one.

| Place | Holds | Who updates it |
| ----- | ----- | -------------- |
| The live graph | the graph the service has loaded | the re-import (step 1) |
| The export folder, `graph.json` and `edges.csv` | the edges of one graph | you, with `export-edges.sh` (step 2) |
| `graph_edge` and `graph_edge_export` in PostgreSQL | a copy of the export | task `9c`, when the export's hash differs from the stored one |
| The tables and the `latest` pointer | depth for one graph | task `9c`, on the next run, or `server_check.sh` (step 3) |

## When a re-import is needed

- The OSM file `hanoi-model-area.osm.pbf` changes.
- The `graphhopper` section of `config.yml` changes in a way that changes the graph: the profiles, `graph.encoded_values`, or `import.osm.ignored_highways`. GraphHopper refuses to load a graph with a profile it has not seen, which forces a re-import ([[graphhopper-backend]]).
- The GraphHopper image changes and the new version reads the graph differently.

A restart that finds a graph in `/data/graph-cache` loads it and changes nothing. That is not a re-import.

## What is stale in between, and what happens to it

From the end of step 1 until step 3 is done, `latest` names a table of the old graph. Nothing breaks today, because nothing in routing reads the table yet. Once the Java reader exists (`US-043`), it refuses that table, names both hashes in the log, and the engine falls back to today's model with the flag set ([[PRD-003-edge-depth-table|edge-depth-table]], Rollback). Python readers use `read_latest_table_for_graph`, which raises `StaleTableError` with both hashes and logs it at ERROR.

The window is short if you do the steps in one go. The next DAG run builds a table from whatever export is in the folder, so a run that starts before step 2 builds a table of the old graph again, and `check_tables.py` says so.

## Procedure

Run the commands from the Mac, in the repo root, unless a step says the server. Commands that start, recreate, or remove a service run on the server over SSH, with `--no-deps` ([[lessons#L-010|recreate-remote-services-on-the-remote-host]]). The server's shell is PowerShell, so use `;` and not `&&`, and its remote for this repository is `alice`.

### 0. Look at the starting state

```bash
docker --context remote-server exec airflow_new-airflow-worker-1 \
  python /opt/airflow/scripts/edge_depth/check_tables.py
```

You expect `FRESH`. Note the hash. If the state is already stale, fix that first.

### 1. Re-import the graph

Put the new OSM file or `config.yml` on the server (`git pull alice <branch>` for the config). Then empty the graph cache and recreate the service, which imports on start:

```bash
docker --context remote-server exec airflow_new-graphhopper-1 sh -c 'rm -rf /data/graph-cache/*'
ssh tecotec@100.67.84.55 "cd C:\Users\TECOTEC\airflow_new; docker compose up -d --force-recreate --no-deps graphhopper"
```

If `ExportEdges` changed, rebuild the image first with `docker compose build graphhopper` from the server's own desktop, because a build over SSH fails.
The import of 2026-10-12 took about 40 seconds, and routing is down until the service is healthy. Wait for `docker --context remote-server ps` to show `graphhopper` as healthy, and check `/info` lists the four profiles. This is the same wipe-and-recreate that resolved [[BL-001-graphhopper-vehicle-profile-rejection|graphhopper-vehicle-profile-rejection]].

### 2. Write the new export

```bash
EXPORT_DEST='D:/airflow_new_data/data/mapping/graph_export' java/time-aware-routing/export-edges.sh
```

Use the export folder of your server (the Airflow data folder, under `mapping/graph_export`). The script checks the row count against the edge count and prints the new `graph_hash=...`. It writes both files in one run, and the files replace the old ones. `EXPECTED_EDGES` defaults to 67,833, the count of the last graph, so a changed graph fails that last line on purpose: set `EXPECTED_EDGES` to the new count when the change is intended.

### 3. Build a table for the new graph

Either wait for the next DAG run, or build now from a retained run:

```bash
scripts/edge_depth/server_check.sh
```

Task `9c`, and `server_check.sh`, load the new export into `graph_edge` because its hash differs from the stored one, sample the run's tiles along the new edges, write `<run>.bin` tagged with the new hash, and move `latest` to it. If `latest` already names a table of a newer run (an old graph's table can be newer than the run you rebuild), the pointer does not move back: run the check in step 4 and rebuild the newest run.

### 4. Check that everything agrees

```bash
docker --context remote-server exec airflow_new-airflow-worker-1 \
  python /opt/airflow/scripts/edge_depth/check_tables.py --graph-hash <the hash step 2 printed>
```

You expect `FRESH`. The command compares the live graph, the export folder, `graph_edge`, and the `latest` table, and it names every mismatch with both hashes. Older kept tables of the old graph show as "not read" and leave when retention removes them.

## The edge key

`edges.csv` of format 3 has a column `edge_key`, written as `<osm_way_id>:<position>`.
The position counts the edges of one OSM way in edge-id order, from 0.
`graph_edge.edge_key` holds it with a unique index, and the key is NULL for every row until an export of format 3 is loaded.
The key needs `osm_way_id` in `graph.encoded_values` of `config.yml`.
Without that value `ExportEdges` fails and writes nothing.

### What the key keeps

The key stays the same when the same OSM file is imported again, even if GraphHopper numbers the edges differently.
A graph imported again from the same file also has the same graph hash, so the edge depth tables stay valid and task `9c` builds nothing new.
`load_graph_edges` still loads the first export of format 3, because it reloads `graph_edge` while an export has keys and a row has none.

### Rule for a changed OSM file

After an import from a changed file, compare the old and the new keys before you trust any history.
Use this rule for the history of a key:

1. A key that is in both graphs and whose way has the same number of edges is the same edge. Keep its history.
2. A key of a way that the new file removed is gone. Do not give its history to another edge.
3. A key of a way whose number of edges changed is not safe. The split points of the way moved, so positions shift. Treat all its keys as new and do not carry history over.
4. A key of a new way is new and has no history.

The tests prove rules 1 and 4 on a small graph (an extra way adds one key and leaves the others unchanged).
No real changed extract was compared yet, so rules 2 and 3 follow from how GraphHopper numbers edges and are not measured.

### Limit

`osm_way_id` is a 31-bit integer, so the import fails when a way id passes 2,147,483,647.
The largest way id of the graph on 2026-10-12 is 1,556,752,106, which is 72.5 percent of that limit.
The import fails with a message that names the way id, so the failure is not silent.

## If something goes wrong

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| `check_tables.py` says the export folder is for another graph than the live one | step 2 did not run, or ran before the import finished | run step 2 again |
| It says the `latest` table is stale and the export is current | step 3 has not built a table yet, or the newest run's table is of the old graph | run step 3, then the check |
| `graph_edge` shows another hash than the export | the table build has not run since step 2 | nothing: the next build reloads it |
| Step 3 fails with no export | the export folder is empty | step 2 |
| `export-edges.sh` fails on `EXPECTED_EDGES` | the new graph has another edge count | check it is the intended graph, then set `EXPECTED_EDGES` |
| Step 3 fails with `column "edge_key" does not exist` | the live `graph_edge` has no `edge_key` yet | run `python /opt/airflow/scripts/database/create_graph_edge_table.py` in the worker, which `0b_ensure_schema` also does on each run |
| The service does not become healthy after step 1 | the import failed | `docker logs airflow_new-graphhopper-1`, and the profile and encoded-value notes in [[graphhopper-backend]] |

To roll back, restore the old OSM file and `config.yml`, and repeat the procedure. The old export is gone, and the new one comes from the restored graph.

## What is built, and what is not

Built and verified on the server on 2026-10-05: the export and its hash (`US-039`), the table and the hash tag (`US-041`), atomic publish (`US-042`), and `check_tables.py` (`US-044`), which says `FRESH` on the real export, `graph_edge` and `latest` table (hash `8c13d884...`) and `STALE`, naming both hashes, against another hash. `StaleTableError` and `read_latest_table_for_graph` are tested, and not yet used by any reader.

Not built yet: the refusal in the Java reader at request time. It is the acceptance of `US-043` (a table for another graph hash is refused and both hashes are named), and the engine that uses the reader comes with `US-050` and `US-052`.

Rehearsed for the first time on 2026-10-07 (host ADMIN), forced by US-051's `td_limit_cm` hints on `truck` and `foot` in `config.yml`: GraphHopper's internal profile-config fingerprint changed ("Profile 'motorbike' does not match. Stored: 1463693215, Configured: -574150319"), which is a different hash from this project's own edge-based `graphHash` and triggers the same refusal independent of whether the edges themselves changed. Steps 0 and 1 only: `check_tables.py` read `FRESH` (hash `8c13d8841f83...`) before the wipe; `/data/graph-cache` was cleared via a one-off container against the named volume (`docker exec` into the crash-looping container itself does not work — it refuses with "is restarting"; `docker compose stop graphhopper` first, then mount the volume from a throwaway container); `docker compose up -d --force-recreate --no-deps graphhopper` became healthy in under 30 seconds (Hanoi's graph is small); `/info` listed all four profiles; the engine log showed `time-aware routing: following /tables for graph hash 8c13d8841f83...`, the same hash as before. Steps 2 and 3 (re-export, rebuild a table) were not needed: the edge topology did not change, only the profile fingerprint did, so `check_tables.py` read `FRESH` again on the same hash with no new export or table build.

## Related

[[edge-depth-table-publish]] covers the pointer and retention. [[edge-depth-table-airflow-task]] covers task `9c`. [[graph-reimport-procedure-and-stale-table-check]] is the plan of this page.
