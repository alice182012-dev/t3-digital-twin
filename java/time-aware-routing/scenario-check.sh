#!/usr/bin/env bash
# Runs the four synthetic flood scenarios through the time-aware search on the server (US-050).
#
# Run from the Mac, in the repo root:   java/time-aware-routing/scenario-check.sh
#
# Builds the image on the server (which runs every module test in the test stage), then runs ScenarioReport in a
# throwaway container. It reads no graph and no table from the server and touches no live service.
set -u

CONTEXT=${CONTEXT:-remote-server}
IMAGE=graphhopper-time-aware:test

d() { docker --context "$CONTEXT" "$@"; }

cd "$(dirname "$0")" || exit 1

echo "== 1. Build the image (runs the module tests in the test stage)"
d build -t "$IMAGE" . || { echo "BUILD FAILED"; exit 1; }

echo "== 2. The four scenarios for motorbike and car, with and without a detour"
d run --rm --entrypoint sh "$IMAGE" -c '
    CP="/opt/time-aware/time-aware-routing.jar:$(ls /graphhopper/graphhopper-web*.jar | head -n 1)"
    exec java -cp "$CP" com.graphhopper.timeaware.ScenarioReport
' 2>&1 | grep -v "^Picked up"
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: a scenario did not match"; exit 1; }
