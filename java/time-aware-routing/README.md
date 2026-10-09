# time-aware-routing

Java module for the flood map's routing. It builds against GraphHopper commit `d7dc1b06` (version `12.0-SNAPSHOT`), the commit the server's stock image was built from.

What is here now (US-049, a skeleton):

- `TimeAwareGraphHopper` is a `GraphHopper` with its own `WeightingFactory`. Today it returns the stock weighting, so the stock profiles route as before.
- `com.graphhopper.http.GraphHopperManaged` is a shadow copy of GraphHopper's class of the same name. `GraphHopperBundle` calls `new GraphHopperManaged(...)`, and the web server has no setting to pick another class. The image puts this module's jar before `graphhopper-web.jar`, so the JVM loads this copy.
- `ExportEdges` writes every edge of a built graph with its id and geometry, plus a hash of the graph (US-039). See below.
- `LandmarkLowerBoundTest` answers whether a weighting that only raises weights keeps the landmark (LM) lower bounds valid.

## Test

CI runs `mvn test` on every push to this folder. To run it yourself you need the pinned GraphHopper in `~/.m2`. The workflow shows how to build it, and so does the first stage of the `Dockerfile`.

```shell
docker build --target test java/time-aware-routing
```

## Run in the image

```shell
docker build -t graphhopper-time-aware java/time-aware-routing
```

The image starts from the stock image's digest and starts GraphHopper with `run-time-aware.sh`, which takes the same `-c` and `-o` options as the stock `graphhopper.sh`. On start the log has the line `TimeAwareGraphHopper active`. If that line is missing, the stock class loaded.

## Start the image beside the live service

`smoke-test.sh` builds the image on the server, starts it on port 8990 with its own graph cache, and compares routes with the live service on port 8989. Run it from the Mac in the repo root, and run `smoke-test.sh cleanup` after. The paths of the server's repo and OSM file are variables at the top of the script.

## Read the edge depth table

- `EdgeDepthTable.open(path)` memory-maps one table read-only and checks it as the Python reader does. `depthCm(edge, step)` returns 0 to 65535. A damaged file throws `TableFormatException`, and `requireGraphHash` throws `StaleTableException` naming both hashes.
- `LatestTableSource(folder, graphHash)` follows the `latest` pointer. `current()` is the table to serve. The poll started by `start()` runs every 5 s (never over 30 s). A damaged or stale new table is logged at ERROR and the valid current one stays. A caller that holds a table keeps it, so a request in flight finishes on its own table.
- `GraphHash.compute(graph)` is the hash that `ExportEdges` writes to `graph.json`.
- `EdgeDepthTableTool <table-folder> [--graph-hash H | --graph-folder DIR] [--watch SECONDS]` reads the table from the command line. `reader-check.sh` runs it in a second container on the server (run from the Mac in the repo root).

## Time-aware search (US-050)

- `StickyClosure` is the closure rule. A road is closed for an arrival when a step in `[departure, arrival + 10 min]` has a depth at or above the vehicle limit. Steps before the departure are ignored.
- `TimeAwareDijkstra` is a Dijkstra search whose labels carry the weight and the time spent. A label is dropped only when another label at the node is no heavier and no later, which keeps it exact when weight and time differ.
- `TimeAwareRouter` (built by `TimeAwareGraphHopper.doCreateRouter`) uses it for a request with the hint `td_departure` (epoch seconds) on a profile with the hint `td_limit_cm`. Any other request is routed as before. A time-aware request skips LM and CH. The table comes from `TimeAwareGraphHopper.setTableSupplier`, which `US-052` connects to `LatestTableSource`.
- `StickyChecker` re-walks a route and lists every road entered while closed.

### Two-option plan (decision D-021)

A time-aware request is planned with the profile's hard limit first. The router then re-walks that route against the precaution depth `P = ceil(fraction * limit)`, in whole cm, using the same window start, departure, and 10-minute margin. The response has these shapes:

- No road of the route reaches `P`: one path, `td.kinds` is `recommended`. No second search runs.
- A road reaches `P` and a second search under `P` finds a route: two paths. Path 0 is the route under `P`, kind `recommended`. Path 1 is the limit route, kind `through_water`. `td.kinds` is `recommended,through_water`.
- A road reaches `P` and no route exists under `P`: one path, the limit route, `td.kinds` is `through_water`.

The fraction is the profile hint `td_precaution_fraction`, a number above 0 and at most 1, read beside `td_limit_cm`. It is 0.5 when the profile has no such hint. A value outside that range gives a `fallback` answer that names the profile. A request cannot set it.

Response hints added to `td.status`, `td.run`, `td.departure`, and `td.last_step`:

- `td.kinds`: a comma list with one kind per path, in path order.
- `td.limit_cm`: the vehicle's limit.
- `td.precaution_cm`: `P` as used, in whole cm.

An answer with `td.status` `fallback`, an error answer, and a request without `td_departure` carry none of the three. `td.status` is `unknown` when the recommended path (path 0) ends after the last forecast step.
- `scenario-check.sh` runs `ScenarioReport` on the server: the four scenarios of the blocker's test table, for the motorbike, car, truck, and foot profile, with and without a detour (32 runs).

## Export the graph's edges

`ExportEdges <graph-cache-folder> <output-folder>` opens the graph cache read-only and writes two files.

- `edges.csv` has the header `edge_id,wkt,base_node,adj_node` and one row per edge, in edge-id order. `wkt` is a quoted LINESTRING in EPSG:4326, longitude first, through the base node, the shape points, and the adjacent node. `base_node` and `adj_node` are the GraphHopper node ids of the edge.
- `graph.json` has `format_version` (2; format 1 had only `edge_id` and `wkt`), `graph_hash`, `edge_count`, `node_count`, and `graphhopper_commit`.

The hash is a SHA-256 over the node count, the edge count, and for each edge in id order its base node, adjacent node, point count, and points in 1e-7 degrees. It reads no file timestamps, so two exports of one graph, and two imports of one OSM file, give one hash. Any change to a node, an edge, or a geometry changes it.

`export-edges.sh` runs it on the server against the live service's graph cache, mounted read-only, and checks the row count. Run it from the Mac in the repo root.

