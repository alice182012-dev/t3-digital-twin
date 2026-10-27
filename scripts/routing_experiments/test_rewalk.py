import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "edge_depth"))

import edge_depth_table  # noqa: E402
import golden_fixture  # noqa: E402
from rewalk import Route, SlowDown, StepRule, rewalk  # noqa: E402

LIMIT = 250


def golden_table():
    table_bytes, _ = golden_fixture.build()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "golden.bin"
        path.write_bytes(table_bytes)
        return edge_depth_table.read_table(path)


TABLE = golden_table()
STEPS = tuple(t.timestamp() for t in TABLE.header.step_times)
T0 = STEPS[0]


def walk(edge_ids, seconds, departure_step, rule, slowdown=None, limit=LIMIT):
    return rewalk(Route(tuple(edge_ids), tuple(seconds)), STEPS[departure_step], STEPS, TABLE.depth_cm, limit, rule, slowdown)


class GoldenFixtureTest(unittest.TestCase):
    def test_the_fixture_has_the_depths_the_hand_built_routes_assume(self):
        self.assertEqual(TABLE.edge_depths_cm(2), (0, 1, 255, 256, 257, 1000, 32767, 32768, 65535))
        self.assertEqual(TABLE.edge_depths_cm(10), (70, 83, 96, 109, 122, 135, 148, 161, 174))
        self.assertEqual(TABLE.edge_depths_cm(29), (203, 216, 229, 242, 255, 268, 281, 294, 307))
        self.assertEqual(STEPS[1] - STEPS[0], 900)


class ThreeEdgeRouteTest(unittest.TestCase):
    """Route 0, 2, 10 leaving at step 1 (900 s). Edge 2 is entered at 1,900 s, 100 s after step 2 (255 cm)."""

    def test_the_step_at_or_before_the_arrival_finds_one_violation(self):
        w = walk([0, 2, 10], [1000, 900, 600], 1, StepRule.AT_OR_BEFORE)
        self.assertEqual(w.arrivals_s, (T0 + 900, T0 + 1900, T0 + 2800))
        self.assertEqual([(v.position, v.edge_id, v.step, v.depth_cm) for v in w.violations], [(1, 2, 2, 255)])
        self.assertEqual(w.violating_edges, 1)
        self.assertEqual(w.worst_over_limit_cm, 5)
        self.assertEqual(w.worst_edge_id, 2)
        self.assertEqual(w.first_violation_s, 1000)

    def test_the_worse_of_the_two_steps_reads_the_later_deeper_step(self):
        w = walk([0, 2, 10], [1000, 900, 600], 1, StepRule.WORSE_OF_TWO)
        self.assertEqual([(v.edge_id, v.step, v.depth_cm) for v in w.violations], [(2, 3, 256)])
        self.assertEqual(w.worst_over_limit_cm, 6)

    def test_the_three_rules_differ_when_the_arrival_is_just_before_a_deep_step(self):
        # Edge 2 is entered at 1,700 s: 800 s after step 1 (1 cm), 100 s before step 2 (255 cm).
        counts = {rule: walk([0, 2, 10], [800, 900, 600], 1, rule).violating_edges for rule in StepRule}
        self.assertEqual(counts, {StepRule.AT_OR_BEFORE: 0, StepRule.NEAREST: 1, StepRule.WORSE_OF_TWO: 1})

    def test_a_route_that_stays_dry_has_no_severity(self):
        w = walk([0, 10], [1000, 1000], 0, StepRule.WORSE_OF_TWO)
        self.assertEqual((w.violating_edges, w.worst_over_limit_cm, w.worst_edge_id, w.first_violation_s), (0, None, None, None))


class StepBoundaryTest(unittest.TestCase):
    def test_an_arrival_exactly_on_a_step_reads_only_that_step_under_every_rule(self):
        # Edge 2 entered at 1,800 s, exactly step 2 (255 cm). Step 3 (256 cm) is not around it.
        for rule in StepRule:
            w = walk([0, 2], [900, 900], 1, rule)
            self.assertEqual([(v.step, v.depth_cm) for v in w.violations], [(2, 255)], rule)

    def test_the_nearest_step_on_a_tie_is_the_earlier_one(self):
        # Edge 2 entered at 1,350 s, halfway between step 1 (1 cm) and step 2 (255 cm).
        self.assertEqual(walk([0, 2], [450, 900], 1, StepRule.NEAREST).violating_edges, 0)

    def test_a_depth_equal_to_the_limit_is_a_violation(self):
        self.assertEqual(walk([2], [60], 2, StepRule.AT_OR_BEFORE, limit=255).violating_edges, 1)

    def test_an_arrival_after_the_last_step_reads_the_last_step_and_is_counted(self):
        w = walk([0, 10], [8000, 60], 0, StepRule.WORSE_OF_TWO, limit=174)
        self.assertEqual([(v.edge_id, v.step) for v in w.violations], [(10, 8)])
        self.assertEqual(w.beyond_horizon, 1)

    def test_several_violations_report_the_count_the_deepest_and_the_first(self):
        w = walk([1, 0, 2], [600, 600, 600], 2, StepRule.AT_OR_BEFORE)
        self.assertEqual(w.violating_edges, 2)
        self.assertEqual((w.worst_edge_id, w.worst_over_limit_cm), (1, 65535 - 250))
        self.assertEqual(w.first_violation_s, 0)

    def test_an_edge_outside_the_table_is_dry_and_counted(self):
        w = walk([TABLE.header.edge_count, 0], [60, 60], 0, StepRule.AT_OR_BEFORE)
        self.assertEqual((w.violating_edges, w.edges_outside_table), (0, 1))


class LengthsAndSpeedTest(unittest.TestCase):
    def test_a_route_from_lengths_and_a_speed_walks_like_the_same_times(self):
        route = Route.from_lengths((0, 2, 10), (10000.0, 9000.0, 6000.0), speed_mps=10.0)
        self.assertEqual(route.edge_seconds, (1000.0, 900.0, 600.0))
        w = rewalk(route, STEPS[1], STEPS, TABLE.depth_cm, LIMIT, StepRule.AT_OR_BEFORE)
        self.assertEqual([(v.edge_id, v.depth_cm) for v in w.violations], [(2, 255)])

    def test_lengths_and_ids_of_different_counts_are_refused(self):
        with self.assertRaises(ValueError):
            Route.from_lengths((0, 2), (10.0,), speed_mps=10.0)


class SensitivityTest(unittest.TestCase):
    """Edge 29 holds 203 cm at step 0, under the limit. Slowed to half speed, the traveller reaches edge 2 after
    step 2 (255 cm) instead of before it."""

    def test_free_flow_reaches_edge_2_before_it_floods(self):
        self.assertEqual(walk([29, 2], [1000, 600], 0, StepRule.AT_OR_BEFORE).violating_edges, 0)

    def test_slowing_deep_edges_moves_the_arrival_onto_the_flooded_step(self):
        w = walk([29, 2], [1000, 600], 0, StepRule.AT_OR_BEFORE, slowdown=SlowDown(min_depth_cm=200, factor=2.0))
        self.assertEqual(w.arrivals_s, (T0, T0 + 2000))
        self.assertEqual([(v.edge_id, v.step, v.depth_cm) for v in w.violations], [(2, 2, 255)])
        self.assertEqual(w.first_violation_s, 2000)

    def test_a_shallow_edge_keeps_its_free_flow_time(self):
        w = walk([29, 2], [1000, 600], 0, StepRule.AT_OR_BEFORE, slowdown=SlowDown(min_depth_cm=204, factor=2.0))
        self.assertEqual(w.arrivals_s, (T0, T0 + 1000))


if __name__ == "__main__":
    unittest.main()
