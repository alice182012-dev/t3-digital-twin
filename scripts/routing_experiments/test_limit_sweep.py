import unittest

import limit_sweep as ls
from limit_sweep import Change, Conclusion, PlanRow, SweepResult
from sticky_reference import Edge, Graph, Route

STEPS = (0, 900)

# Road 0-1 has edges 0 and 4, road 1-3 has edges 1 and 5. The detour 0 -> 2 -> 3 is one way.
GRAPH = Graph(
    [
        Edge(0, 0, 1, 100),
        Edge(4, 1, 0, 100),
        Edge(1, 1, 3, 100),
        Edge(5, 3, 1, 100),
        Edge(2, 0, 2, 150),
        Edge(3, 2, 3, 150),
    ]
)
DEPTHS = {1: [25, 25], 5: [25, 25]}


def depth_cm(edge_id, step):
    return DEPTHS.get(edge_id, [0, 0])[step]


def length_m(edge_id):
    return GRAPH.edge(edge_id).seconds * 10


def road_key(edge_id):
    return {4: 0, 5: 1}.get(edge_id, edge_id)


def sweep(pairs=((0, 3), (3, 0)), plan_limits=(20, 30), judge_limits=(20, 30), **kw):
    return ls.sweep(GRAPH, pairs, 0, 0, STEPS, depth_cm, length_m, plan_limits, judge_limits, **kw)


class PlanSingleTimestepTest(unittest.TestCase):
    def test_closes_edges_whose_departure_step_depth_reaches_the_limit(self):
        at_departure = lambda edge_id: depth_cm(edge_id, 0)
        self.assertEqual(ls.plan_single_timestep(GRAPH, 0, 3, 0, at_departure, 30), Route((0, 1), (0, 100), 200))
        self.assertEqual(ls.plan_single_timestep(GRAPH, 0, 3, 0, at_departure, 25), Route((2, 3), (0, 150), 300))
        self.assertIsNone(ls.plan_single_timestep(GRAPH, 3, 0, 0, at_departure, 25))

    def test_arrival_times_start_at_the_departure(self):
        route = ls.plan_single_timestep(GRAPH, 0, 3, 40, lambda e: 0, 30)
        self.assertEqual((route.arrivals_s, route.end_s), ((40, 140), 240))


class JudgeTest(unittest.TestCase):
    def test_reads_the_step_at_or_before_each_entry(self):
        route = Route((2, 3), (0, 900), 1050)
        by_step = {3: [0, 40]}
        violations = ls.judge(route, 0, STEPS, lambda e, s: by_step.get(e, [0, 0])[s], 30)
        self.assertEqual([(v.edge_id, v.step, v.depth_cm) for v in violations], [(3, 1, 40)])

    def test_a_depth_equal_to_the_limit_is_a_violation(self):
        route = Route((1,), (0,), 100)
        self.assertEqual(len(ls.judge(route, 0, STEPS, depth_cm, 25)), 1)
        self.assertEqual(len(ls.judge(route, 0, STEPS, depth_cm, 26)), 0)


class SweepTest(unittest.TestCase):
    def test_rows_by_plan_limit(self):
        result = sweep(road_key=road_key)
        self.assertEqual(
            result.rows,
            (
                PlanRow(20, closed_km=1.0, route_share=0.5, mean_detour_s=100.0, violation_rate=0.0),
                PlanRow(30, closed_km=0.0, route_share=1.0, mean_detour_s=0.0, violation_rate=0.0),
            ),
        )
        self.assertEqual((result.n_pairs, result.n_dry_unreachable), (2, 0))

    def test_closed_length_counts_each_edge_when_no_road_key_is_given(self):
        self.assertEqual(sweep().rows[0].closed_km, 2.0)

    def test_regret_table_plans_with_one_limit_and_judges_with_another(self):
        regret = sweep().regret
        self.assertEqual(regret[(20, 20)], 0.0)
        self.assertEqual(regret[(20, 30)], 0.0)
        self.assertEqual(regret[(30, 30)], 0.0)
        self.assertEqual(regret[(30, 20)], 1.0)

    def test_a_pair_with_no_dry_route_is_left_out_and_counted(self):
        result = sweep(pairs=((0, 3), (0, 9)))
        self.assertEqual((result.n_pairs, result.n_dry_unreachable), (1, 1))
        self.assertEqual(result.rows[0].route_share, 1.0)

    def test_a_plan_with_no_routed_pair_has_no_rates(self):
        result = sweep(pairs=((3, 0),), plan_limits=(25,), judge_limits=(25,))
        self.assertEqual(result.rows[0], PlanRow(25, 2.0, 0.0, None, None))
        self.assertIsNone(result.regret[(25, 25)])


def result(shares, violation_rates):
    rows = tuple(PlanRow(limit, 0.0, shares[limit], 0.0, violation_rates[limit]) for limit in shares)
    return SweepResult(rows, {}, 10, 0)


class ConclusionTest(unittest.TestCase):
    def test_conclusion_is_the_limits_with_violations_and_the_route_share_rank(self):
        r = result({20: 0.5, 30: 1.0, 40: 1.0}, {20: 0.0, 30: 0.2, 40: 0.0})
        self.assertEqual(Conclusion.of(r), Conclusion(frozenset({30}), (30, 40, 20)))

    def test_lists_settings_that_differ_from_the_baseline(self):
        base = result({20: 0.5, 30: 1.0}, {20: 0.0, 30: 0.2})
        same_rank_fewer_violations = result({20: 0.6, 30: 0.9}, {20: 0.0, 30: 0.0})
        flipped_rank = result({20: 1.0, 30: 0.5}, {20: 0.0, 30: 0.2})
        results = {"base": base, "dry": same_rank_fewer_violations, "flipped": flipped_rank, "same": base}
        self.assertEqual(
            ls.conclusion_changes(results, "base"),
            [Change("dry", violations_changed=True, rank_changed=False),
             Change("flipped", violations_changed=False, rank_changed=True)],
        )

    def test_settings_with_different_plan_limits_cannot_be_compared(self):
        with self.assertRaises(ValueError):
            ls.conclusion_changes({"a": result({20: 1.0}, {20: 0.0}), "b": result({30: 1.0}, {30: 0.0})}, "a")


if __name__ == "__main__":
    unittest.main()
