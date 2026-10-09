#!/usr/bin/env bash
# Runs the tests of the US-101 rain gate and flood rule from the repository root.
set -u
cd "$(git rev-parse --show-toplevel)"
echo "captured: $(date '+%F %T %z') on $(hostname -s), commit $(git rev-parse --short HEAD)"
(cd scripts && python3 -m pytest test_standing_flood.py -v 2>&1 | grep -E "PASSED|FAILED|passed|failed" | sed 's/^test_standing_flood.py:://; s/ *\[ *[0-9]*%\]//')
python3 -m pytest test/test_flood_mapping_dag_graph.py -v -k "dry_state or threshold or standing_flood" 2>&1 | grep -E "PASSED|FAILED|passed|failed" | sed 's#^test/test_flood_mapping_dag_graph.py::FloodMappingDagGraphTests::##; s/ *\[ *[0-9]*%\]//'
