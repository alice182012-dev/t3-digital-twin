# The end-of-test check of US-034. Run it after 2026-10-04 16:00 +07. It also runs earlier as an interim check.
cd "$(git rev-parse --show-toplevel)" || exit 1
echo "Host: $(hostname), $(uname -sm), Python $(python3 --version | cut -d' ' -f2)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo "Soak window: 2026-10-02 16:00 +07 to 2026-10-04 16:00 +07 (48 hours), under the replay of US-063"
echo
sh scripts/backend_soak/run_soak.sh 2026-10-02T16:00:00+07:00 2>&1 | cut -c1-170
echo "run_soak.sh exit code: ${PIPESTATUS[0]}"
