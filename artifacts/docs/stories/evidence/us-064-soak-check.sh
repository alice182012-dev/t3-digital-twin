cd "$(git rev-parse --show-toplevel)/scripts/backend_soak" || exit 1
echo "Host: $(hostname), $(uname -sm), Python $(python3 --version | cut -d' ' -f2)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. tests of the soak tooling, the new ones for US-064 included"
python3 -m pytest -v -p no:cacheprovider --color=no test_soak_checks.py test_run_soak.py 2>&1 | sed -n '/collected/,$p' | sed 's/ *\[ *[0-9]*%\]//' | grep -E "RunLogsTest|JudgeContainersTest|RunSoakTest|passed|failed"
FAKES=$(mktemp -d)
cat >"$FAKES/ssh" <<'SH'
#!/bin/sh
cat >/dev/null
echo '2026-10-02T01:00:00.000000000Z INFO  [2026-10-02 01:00:00,000] com.graphhopper.resources.RouteResource: points: 2'
SH
cat >"$FAKES/docker-down" <<'SH'
#!/bin/sh
echo 'request returned 500 Internal Server Error for API route and version http://docker.example.com/v1.56/containers/json, check if the server supports the requested API version' >&2
exit 1
SH
cat >"$FAKES/docker-up" <<'SH'
#!/bin/sh
shift 2
case "$1" in
	inspect) for last; do :; done; echo "/$last started=2026-09-24T03:10:11.123456789Z restarts=0 oomkilled=false status=running" ;;
	logs) echo '2026-10-02T01:00:00.000000000Z 172.18.0.1 - - [02/Oct/2026:01:00:00 +0000] "POST /api/gh/route?key= HTTP/1.1" 200 2096 "-" "UA"' ;;
	exec) exit 0 ;;
esac
SH
chmod +x "$FAKES"/*
echo
echo "2. the outage of 2026-10-02 13:53 +07, replayed: every docker call answers HTTP 500"
mkdir "$FAKES/down" && cp "$FAKES/ssh" "$FAKES/down/ssh" && cp "$FAKES/docker-down" "$FAKES/down/docker"
OUT=$(PATH="$FAKES/down:$PATH" sh run_soak.sh 2>&1); CODE=$?
echo "$OUT" | grep -E "^FAILED|^containers exit|could not read" | cut -c1-175
echo "run_soak.sh exit code: $CODE"
echo
echo "3. a healthy server, the same script"
mkdir "$FAKES/up" && cp "$FAKES/ssh" "$FAKES/up/ssh" && cp "$FAKES/docker-up" "$FAKES/up/docker"
OUT=$(PATH="$FAKES/up:$PATH" sh run_soak.sh 2>&1); CODE=$?
echo "$OUT" | grep -E "^FAILED|^containers exit" | cut -c1-175
echo "run_soak.sh exit code: $CODE"
rm -rf "$FAKES"
