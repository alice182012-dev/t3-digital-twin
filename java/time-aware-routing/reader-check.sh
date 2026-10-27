#!/usr/bin/env bash
# Checks the Java reader of the edge depth table on the server (US-043), in a second container.
#
# Run from the Mac, in the repo root:   java/time-aware-routing/reader-check.sh
#
# Needs a published table (scripts/edge_depth/server_check.sh), so `latest` exists in the volume edge-depth-tables.
# The reader container mounts the table volume and the live graph cache, both read-only. The real `latest` is never
# moved: step 4 publishes into a scratch folder inside the same volume, from the Airflow worker.
set -u

CONTEXT=${CONTEXT:-remote-server}
TABLE_VOLUME=${TABLE_VOLUME:-airflow_new_edge-depth-tables}
CACHE_VOLUME=${CACHE_VOLUME:-airflow_new_graphhopper-graph-cache}
WORKER=${WORKER:-airflow_new-airflow-worker-1}
TABLE_DIR=${TABLE_DIR:-/opt/airflow/edge_depth_tables}
IMAGE=graphhopper-time-aware:test
SCRATCH=.reader-check

d() { docker --context "$CONTEXT" "$@"; }

# Runs the tool in a throwaway reader container. Extra docker run flags come first, then `--`, then tool arguments.
tool() {
    local flags=()
    while [ "$1" != "--" ]; do flags+=("$1"); shift; done
    shift
    d run --rm ${flags[@]+"${flags[@]}"} --entrypoint sh \
        --mount "type=volume,source=$TABLE_VOLUME,target=/tables,readonly" \
        --mount "type=volume,source=$CACHE_VOLUME,target=/data/graph-cache,readonly" \
        "$IMAGE" -c '
            CP="/opt/time-aware/time-aware-routing.jar:$(ls /graphhopper/graphhopper-web*.jar | head -n 1)"
            exec java -cp "$CP" com.graphhopper.timeaware.EdgeDepthTableTool "$@"
        ' sh "$@" 2>&1 | grep -v "^Picked up"
    return "${PIPESTATUS[0]}"
}

cd "$(dirname "$0")" || exit 1

echo "== 1. Build the image (runs the module tests in the test stage)"
d build -t "$IMAGE" . || { echo "BUILD FAILED"; exit 1; }

echo "== 2. The real table, read in a second container, against the hash of the live graph"
tool -- /tables --graph-folder /data/graph-cache
[ $? -eq 0 ] || { echo "FAIL: the real table was not read, or it does not match the live graph"; exit 1; }

echo "== 3. A graph hash that is not the live one must be refused (exit 1) and name both hashes"
tool -- /tables --graph-hash 0000000000000000000000000000000000000000000000000000000000000000
[ $? -eq 1 ] || { echo "FAIL: the stale case did not exit with 1"; exit 1; }

echo "== 4. A new latest, published by the worker while the reader runs, is loaded without a restart"
d exec -i "$WORKER" python - <<PY || { echo "SETUP FAILED"; exit 1; }
import shutil, sys
from pathlib import Path
sys.path.insert(0, "/opt/airflow/scripts/edge_depth")
import edge_depth_table as t
table_dir = Path("$TABLE_DIR")
scratch = table_dir / "$SCRATCH"
shutil.rmtree(scratch, ignore_errors=True)
scratch.mkdir()
shutil.copy(t.read_latest(table_dir), scratch / "20990101T000000.bin")
t.write_latest(scratch, "20990101T000000.bin")
print("scratch folder ready, latest -> 20990101T000000.bin")
PY
(
    sleep 8
    d exec -i "$WORKER" python - <<PY
import shutil, sys
from pathlib import Path
sys.path.insert(0, "/opt/airflow/scripts/edge_depth")
import edge_depth_table as t
scratch = Path("$TABLE_DIR") / "$SCRATCH"
shutil.copy(t.read_latest(scratch), scratch / "20990101T010000.bin")
t.write_latest(scratch, "20990101T010000.bin")
print("worker: published 20990101T010000.bin")
PY
) &
publisher=$!
tool -- /tables/$SCRATCH --watch 20 | tee /tmp/reader-check-watch.txt
status=${PIPESTATUS[0]}
wait $publisher
d exec "$WORKER" rm -rf "$TABLE_DIR/$SCRATCH"
grep -q "serving table=20990101T000000.bin" /tmp/reader-check-watch.txt \
    && grep -q "serving table=20990101T010000.bin (loaded from the pointer without a restart)" /tmp/reader-check-watch.txt \
    && [ "$status" -eq 0 ] \
    && echo "PASS: the reader switched tables within 20 s with no restart" \
    || { echo "FAIL: the reader did not switch tables"; exit 1; }
