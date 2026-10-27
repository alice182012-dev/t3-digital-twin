#!/usr/bin/env bash
# Exports the edges of the live GraphHopper graph on the server (US-039), twice, and checks the result.
#
# Run from the Mac, in the repo root:   java/time-aware-routing/export-edges.sh
#
# The graph cache of the live service is mounted read-only, so the live service is not touched.
#
# By default the files go into the throwaway container, so only the printed result is kept. To keep the export for
# the Airflow edge depth table task (US-041), set EXPORT_DEST to a folder on the server that Airflow reads, which
# is <DATA_HOST_PATH>\mapping\graph_export on the server, and create the folder first:
#   EXPORT_DEST='D:/airflow_new_data/data/mapping/graph_export' java/time-aware-routing/export-edges.sh
set -u

CONTEXT=${CONTEXT:-remote-server}
CACHE_VOLUME=${CACHE_VOLUME:-airflow_new_graphhopper-graph-cache}
EXPORT_DEST=${EXPORT_DEST:-}
EXPECTED_EDGES=${EXPECTED_EDGES:-67833}   # the edge count that US-046 recorded in routing-not-time-aware.md
IMAGE=${IMAGE:-graphhopper-time-aware:test}
SKIP_BUILD=${SKIP_BUILD:-}   # set to 1 to use an image already on the server, for example IMAGE=graphhopper-time-aware:local

d() { docker --context "$CONTEXT" "$@"; }

cd "$(dirname "$0")" || exit 1

if [ -z "$SKIP_BUILD" ]; then
    echo "== 1. Build the image (runs the module tests in the test stage)"
    d build -t "$IMAGE" . || { echo "BUILD FAILED"; exit 1; }
else
    echo "== 1. Skip the build, use the image $IMAGE"
    d image inspect "$IMAGE" >/dev/null 2>&1 || { echo "Image $IMAGE not found on the server"; exit 1; }
fi

echo "== 2. Check that the live graph cache volume exists"
d volume inspect "$CACHE_VOLUME" >/dev/null 2>&1 || {
    echo "Volume $CACHE_VOLUME not found. Volumes with 'graph' in the name:"
    d volume ls | grep -i graph
    echo "Run again with CACHE_VOLUME=<name>."
    exit 1
}

echo "== 3. Export twice from the read-only graph cache"
output=$(d run --rm --entrypoint sh \
    --mount "type=volume,source=$CACHE_VOLUME,target=/data/graph-cache,readonly" \
    "$IMAGE" -c '
        set -e
        CP="/opt/time-aware/time-aware-routing.jar:$(ls /graphhopper/graphhopper-web*.jar | head -n 1)"
        java -cp "$CP" com.graphhopper.timeaware.ExportEdges /data/graph-cache /tmp/out1
        java -cp "$CP" com.graphhopper.timeaware.ExportEdges /data/graph-cache /tmp/out2
        echo "--- graph.json"
        cat /tmp/out1/graph.json
        echo "--- edges.csv: lines including the header, then the first 3 rows"
        wc -l < /tmp/out1/edges.csv
        head -n 4 /tmp/out1/edges.csv | cut -c1-160
        echo "--- the two exports"
        cmp /tmp/out1/edges.csv /tmp/out2/edges.csv && echo "edges.csv identical"
        cmp /tmp/out1/graph.json /tmp/out2/graph.json && echo "graph.json identical"
    ' 2>&1)
status=$?
echo "$output" | grep -v "^Picked up"
[ $status -eq 0 ] || { echo "EXPORT FAILED"; exit 1; }

echo "== 4. Check the row count against the edge count"
edge_count=$(echo "$output" | sed -n 's/.*"edge_count" : \([0-9]*\).*/\1/p')
lines=$(echo "$output" | awk '/^--- edges.csv/ {getline; print; exit}')
echo "edge_count in graph.json: $edge_count   rows in edges.csv: $((lines - 1))   expected from US-046: $EXPECTED_EDGES"
[ "$((lines - 1))" = "$edge_count" ] || { echo "FAIL: rows differ from edge_count"; exit 1; }
if [ "$edge_count" = "$EXPECTED_EDGES" ]; then
    echo "PASS"
else
    echo "NOTE: edge_count differs from $EXPECTED_EDGES. The graph may have been rebuilt since US-046. Set EXPECTED_EDGES if that is expected."
    exit 1
fi

if [ -n "$EXPORT_DEST" ]; then
    echo "== 5. Write the export to $EXPORT_DEST for the Airflow task"
    d run --rm --entrypoint sh \
        --mount "type=volume,source=$CACHE_VOLUME,target=/data/graph-cache,readonly" \
        --mount "type=bind,source=$EXPORT_DEST,target=/out" \
        "$IMAGE" -c '
            set -e
            CP="/opt/time-aware/time-aware-routing.jar:$(ls /graphhopper/graphhopper-web*.jar | head -n 1)"
            java -cp "$CP" com.graphhopper.timeaware.ExportEdges /data/graph-cache /out
            ls -l /out
        ' 2>&1 | grep -v "^Picked up"
    [ "${PIPESTATUS[0]}" -eq 0 ] || { echo "WRITING THE EXPORT FAILED (does the folder exist on the server?)"; exit 1; }
fi
