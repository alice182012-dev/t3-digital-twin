#!/usr/bin/env bash
# Builds the time-aware image on the server, starts it beside the live GraphHopper, and compares routes.
#
# Run from the Mac, in the repo root:   java/time-aware-routing/smoke-test.sh
# Remove the test container after:      java/time-aware-routing/smoke-test.sh cleanup
#
# The container reads the same OSM file and config files as the live service, into its own graph cache.
# The live service is not touched. Edit the paths below if the server's folders differ.
set -u

CONTEXT=${CONTEXT:-remote-server}
SERVER_HOST=${SERVER_HOST:-100.67.84.55}
SERVER_REPO=${SERVER_REPO:-'C:\Users\TECOTEC\airflow_new'}
PBF=${PBF:-'C:\Users\TECOTEC\grasshopper-routing\osm\hanoi-model-area.osm.pbf'}
LIVE_PORT=${LIVE_PORT:-8989}
TEST_PORT=${TEST_PORT:-8990}
NAME=graphhopper-time-aware
IMAGE=graphhopper-time-aware:test
CACHE_VOLUME=graphhopper-time-aware-cache
CONFIG_DIR="$SERVER_REPO"'\floodmap\graphhopper-flood-road\graphhopper'

d() { docker --context "$CONTEXT" "$@"; }

if [ "${1:-}" = cleanup ]; then
    d rm -f "$NAME"
    d volume rm "$CACHE_VOLUME"
    exit 0
fi

cd "$(dirname "$0")" || exit 1

echo "== 1. Build the image (runs the module tests in the test stage)"
d build -t "$IMAGE" . || { echo "BUILD FAILED"; exit 1; }

echo "== 2. Start it on port $TEST_PORT with its own graph cache"
d rm -f "$NAME" >/dev/null 2>&1
d volume create "$CACHE_VOLUME" >/dev/null
mounts=(--mount "type=bind,source=$PBF,target=/data/hanoi-model-area.osm.pbf,readonly"
        --mount "type=volume,source=$CACHE_VOLUME,target=/data/graph-cache")
for f in config.yml motorbike.json car_custom.json truck_custom.json foot_custom.json foot_avoid_private_node_custom.json; do
    mounts+=(--mount "type=bind,source=$CONFIG_DIR\\$f,target=/graphhopper/$f,readonly")
done
d run -d --name "$NAME" -p "$TEST_PORT:8989" "${mounts[@]}" "$IMAGE" -c config.yml -o /data/graph-cache || exit 1

echo "== 3. Wait for the import and the landmarks, up to 10 minutes"
ready=no
for _ in $(seq 1 60); do
    if curl -fsS -m 5 "http://$SERVER_HOST:$TEST_PORT/health" >/dev/null 2>&1; then ready=yes; break; fi
    if [ "$(d inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" != true ]; then break; fi
    sleep 10
done

echo "== 4. Log lines that matter"
d logs "$NAME" 2>&1 | grep -E "Executing|TimeAwareGraphHopper active|ERROR|Exception|No such file" | head -20
[ "$ready" = yes ] || { echo "NOT READY. Last 30 log lines:"; d logs --tail 30 "$NAME" 2>&1; exit 1; }

echo "== 5. Compare routes with the live service (points inside the model border)"
python3 - "$SERVER_HOST" "$LIVE_PORT" "$TEST_PORT" <<'PY'
import json, sys, urllib.request

host, live, test = sys.argv[1], sys.argv[2], sys.argv[3]
# [longitude, latitude], inside the model border of .claude/CLAUDE.md
pairs = [
    [[105.7550, 21.0250], [105.7620, 21.0255]],
    [[105.7100, 21.0000], [105.7500, 21.0200]],
    [[105.7200, 20.9900], [105.7800, 21.0100]],
]

def route(port, profile, points):
    body = {"profile": profile, "points": points, "points_encoded": False, "ch.disable": True, "instructions": False}
    request = urllib.request.Request(
        f"http://{host}:{port}/route", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        path = json.load(urllib.request.urlopen(request, timeout=120))["paths"][0]
        return round(path["distance"], 1), path["time"], len(path["points"]["coordinates"])
    except Exception as error:
        return "ERR " + str(error)[:50]

different = 0
for profile in ["motorbike", "car", "truck", "foot"]:
    for points in pairs:
        a, b = route(live, profile, points), route(test, profile, points)
        same = a == b
        different += not same
        print(f"{profile:10} {'same' if same else 'DIFF'}  live={a}  time-aware={b}")
print("routes compared:", 4 * len(pairs), " different:", different)
sys.exit(1 if different else 0)
PY
