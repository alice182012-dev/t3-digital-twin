import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SINCE = "2026-10-02T00:45:00+07:00"

DOCKER_500 = "request returned 500 Internal Server Error for API route and version http://docker.example.com/v1.56/containers/json, check if the server supports the requested API version"
NGINX_OK = '2026-10-02T01:00:00.000000000Z 172.18.0.1 - - [02/Oct/2026:01:00:00 +0000] "POST /api/gh/route?key= HTTP/1.1" 200 2096 "-" "UA"'
GH_ROUTE = "2026-10-02T01:00:00.000000000Z INFO  [2026-10-02 01:00:00,000] com.graphhopper.resources.RouteResource: points: 2"

DOCKER_DOWN = f"""#!/bin/sh
echo '{DOCKER_500}' >&2
exit 1
"""

DOCKER_UP = f"""#!/bin/sh
shift 2
case "$1" in
	inspect)
		for last; do :; done
		echo "/$last started=2026-09-24T03:10:11.123456789Z restarts=0 oomkilled=false status=running"
		;;
	logs) echo '{NGINX_OK}' ;;
	exec) exit 0 ;;
esac
"""

SSH_UP = f"""#!/bin/sh
cat >/dev/null
echo '{GH_ROUTE}'
"""


def run_soak(docker_script, ssh_script=SSH_UP):
    with tempfile.TemporaryDirectory() as folder:
        for name, body in (("docker", docker_script), ("ssh", ssh_script)):
            path = Path(folder) / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        env = {**os.environ, "PATH": f"{folder}:{os.environ['PATH']}"}
        done = subprocess.run(
            ["sh", str(HERE / "run_soak.sh"), SINCE], capture_output=True, text=True, env=env, timeout=60
        )
    return done.returncode, done.stdout + done.stderr


class RunSoakTest(unittest.TestCase):
    def test_a_docker_outage_fails_the_soak_and_names_each_failed_call(self):
        code, out = run_soak(DOCKER_DOWN)
        self.assertEqual(code, 1)
        self.assertIn("FAILED: docker inspect airflow_new-graphhopper-1", out)
        self.assertIn("FAILED: docker logs airflow_new-floodmap-backend-1", out)
        self.assertNotIn("logs exit 0", out)

    def test_an_ssh_failure_that_leaves_the_graphhopper_log_without_lines_fails_the_soak(self):
        ssh_down = "#!/bin/sh\ncat >/dev/null\necho 'ssh: connect to host 100.67.84.55 port 22: Operation timed out' >&2\nexit 255\n"
        code, out = run_soak(DOCKER_UP, ssh_down)
        self.assertEqual(code, 1)
        self.assertIn("no timestamped lines", out)

    def test_a_healthy_server_passes(self):
        code, out = run_soak(DOCKER_UP)
        self.assertEqual(code, 0, out)
        self.assertNotIn("FAILED", out)


if __name__ == "__main__":
    unittest.main()
