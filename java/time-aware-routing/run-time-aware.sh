#!/bin/sh
# Starts GraphHopper like the stock graphhopper.sh does, with the same -c and -o options, but from the classpath.
# The stock script runs `java -jar graphhopper-web.jar`, which ignores the classpath. Here this module's jar comes
# first, so the JVM loads its GraphHopperManaged before the stock one.
set -e

CONFIG=config.yml
GRAPH=/data/graph-cache
ACTION=server
while [ $# -gt 0 ]; do
    case "$1" in
        -c|--config) CONFIG="$2"; shift 2 ;;
        -o|--graph-cache) GRAPH="$2"; shift 2 ;;
        --import) ACTION=import; shift ;;
        *) echo "run-time-aware.sh: unknown option $1" >&2; exit 2 ;;
    esac
done

STOCK_JAR=$(ls /graphhopper/graphhopper-web*.jar | head -n 1)
echo "## Executing $ACTION with time-aware-routing.jar before $STOCK_JAR"
# JAVA_OPTS is meant to split into words.
# shellcheck disable=SC2086
exec java $JAVA_OPTS -Ddw.graphhopper.graph.location="$GRAPH" \
    -cp "/opt/time-aware/time-aware-routing.jar:$STOCK_JAR" \
    com.graphhopper.application.GraphHopperApplication "$ACTION" "$CONFIG"
