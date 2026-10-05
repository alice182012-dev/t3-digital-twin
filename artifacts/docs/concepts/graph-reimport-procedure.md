---
date: 2026-10-05
type: concept
status: active
tags: [graphhopper, reimport, edge-depth-table, graph-hash, operations]
related: ["[[edge-depth-table-format]]", "[[edge-depth-table-publish]]", "[[edge-depth-table-airflow-task]]", "[[graph-reimport-procedure-and-stale-table-check]]", "[[graphhopper-backend]]", "[[edge-depth-table-stories]]", "[[recreate-remote-services-on-the-remote-host]]"]
last_updated: 2026-10-05
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

From the end of step 1 until step 3 is done, `latest` names a table of the old graph. Nothing breaks today, because nothing in routing reads the table yet. Once the Java reader exists (`US-043`), it refuses that table, names both hashes in the log, and the engine falls back to today's model with the flag set ([[edge-depth-table]], Rollback). Python readers use `read_latest_table_for_graph`, which raises `StaleTableError` with both hashes and logs it at ERROR.

The window is short if you do the steps in one go. The next DAG run builds a table from whatever export is in the folder, so a run that starts before step 2 builds a table of the old graph again, and `check_tables.py` says so.

## Procedure

Run the commands from the Mac, in the repo root, unless a step says the server. Commands that start, recreate, or remove a service run on the server over SSH, with `--no-deps` ([[recreate-remote-services-on-the-remote-host]]). The server's shell is PowerShell, so use `;` and not `&&`, and its remote for this repository is `alice`.

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

The import takes minutes, and routing is down until the service is healthy. Wait for `docker --context remote-server ps` to show `graphhopper` as healthy, and check `/info` lists the four profiles. This is the same wipe-and-recreate that resolved [[graphhopper-vehicle-profile-rejection]].

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

## If something goes wrong

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| `check_tables.py` says the export folder is for another graph than the live one | step 2 did not run, or ran before the import finished | run step 2 again |
| It says the `latest` table is stale and the export is current | step 3 has not built a table yet, or the newest run's table is of the old graph | run step 3, then the check |
| `graph_edge` shows another hash than the export | the table build has not run since step 2 | nothing: the next build reloads it |
| Step 3 fails with no export | the export folder is empty | step 2 |
| `export-edges.sh` fails on `EXPECTED_EDGES` | the new graph has another edge count | check it is the intended graph, then set `EXPECTED_EDGES` |
| The service does not become healthy after step 1 | the import failed | `docker logs airflow_new-graphhopper-1`, and the profile and encoded-value notes in [[graphhopper-backend]] |

To roll back, restore the old OSM file and `config.yml`, and repeat the procedure. The old export is gone, and the new one comes from the restored graph.

## What is built, and what is not

Built and verified on the server on 2026-10-05: the export and its hash (`US-039`), the table and the hash tag (`US-041`), atomic publish (`US-042`), `StaleTableError`, `read_latest_table_for_graph`, and `check_tables.py` (`US-044`).

Not built yet: the refusal in the Java reader at request time. It is the acceptance of `US-043` (a table for another graph hash is refused and both hashes are named), and the engine that uses the reader comes with `US-050` and `US-052`. A full re-import of the live graph has not been rehearsed, because it takes routing down. The steps above come from the commands that exist and from the earlier wipe-and-recreate of the cache.

## Related

[[edge-depth-table-publish]] covers the pointer and retention. [[edge-depth-table-airflow-task]] covers task `9c`. [[graph-reimport-procedure-and-stale-table-check]] is the plan of this page.
