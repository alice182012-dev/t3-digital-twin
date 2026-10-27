cd "$(git rev-parse --show-toplevel)/scripts/routing_reference" || exit 1
echo "Host: $(hostname), $(uname -sm), Python $(python3 --version | cut -d' ' -f2)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. tests of the reference, the checker, the corridor builder, and the scenarios"
python3 -m pytest -v -p no:cacheprovider --color=no 2>&1 | grep -E "brute_force|sticky_column|plain_shortest|reaches_the_corridor|never_crosses|equal_the_backends|passed|failed" | sed 's/ *\[ *[0-9]*%\]//' | grep -E "PASSED$|passed|failed"
echo
echo "2. the four scenarios on real Hanoi roads (21.0250, 105.7550 to 21.0255, 105.7620, inside the model border)"
python3 run_scenarios.py ../../marie-curie/raster-first/roads.geojson 21.0250 105.7550 21.0255 105.7620
