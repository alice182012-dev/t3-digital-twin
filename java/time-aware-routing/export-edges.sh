#!/usr/bin/env bash
# Exports the edges of the live GraphHopper graph on the server (US-039), twice, and checks the result.
#
# Run from the Mac, in the repo root:   java/time-aware-routing/export-edges.sh
#
# The graph cache of the live service is mounted read-only, so the live service is not touched. The files go into
# the throwaway container, so only the printed result is kept.
set -u

CONTEXT=${CONTEXT:-remote-server}
CACHE_VOLUME=${CACHE_VOLUME:-airflow_new_graphhopper-graph-cache}
EXPECTED_EDGES=${EXPECTED_EDGES:-67833}   # the edge count that US-046 recorded in routing-not-time-aware.md
IMAGE=graphhopper-time-aware:test

d() { docker --context "$CONTEXT" "$@"; }

cd "$(dirname "$0")" || exit 1

echo "== 1. Build the image (runs the module tests in the test stage)"
d build -t "$IMAGE" . || { echo "BUILD FAILED"; exit 1; }

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
