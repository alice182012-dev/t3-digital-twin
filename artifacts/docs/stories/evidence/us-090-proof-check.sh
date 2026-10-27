#!/usr/bin/env bash
# Evidence for US-090. Read-only. Run from the repository root on the Mac.
P=artifacts/docs/concepts/sticky-closure-proof.md
echo "--- headings of $P"
grep -n "^## \|^### " $P
echo "--- boundary tests"
grep -n "def test_an_arrival_exactly_on_a_step\|def test_a_departure_between_two_steps\|def test_the_end_of_the_window_is_included\|def test_a_depth_equal_to_the_limit_closes\|def test_water_that_drained_before" scripts/routing_reference/test_sticky_reference.py | cut -c1-120
echo "--- suite"
(cd scripts/routing_reference && python3 -m pytest -q 2>&1 | tail -2)
