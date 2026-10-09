import unittest

from arrival_only import ArrivalOnlyClosure, ArrivalOnlyResult, earliest_arrival_arrival_only
from sticky_reference import Edge, Graph, Route

STEPS = (0, 900, 1800)


def closure(by_edge, limit_cm=20):
    return ArrivalOnlyClosure(STEPS, lambda edge_id, step: by_edge.get(edge_id, [0, 0, 0])[step], limit_cm)


class ClosureTest(unittest.TestCase):
    def test_reads_the_step_at_or_before_the_arrival(self):
        rule = closure({7: [0, 30, 0]})
        self.assertFalse(rule.is_closed(7, 899))
        self.assertTrue(rule.is_closed(7, 900))
        self.assertTrue(rule.is_closed(7, 1799))
        self.assertFalse(rule.is_closed(7, 1800))

    def test_a_depth_equal_to_the_limit_closes(self):
        self.assertTrue(closure({7: [20, 0, 0]}).is_closed(7, 0))

    def test_before_the_first_step_reads_step_zero_and_after_the_last_reads_the_last(self):
        rule = closure({7: [30, 0, 30]})
        self.assertTrue(rule.is_closed(7, -500))
        self.assertTrue(rule.is_closed(7, 99_999))

    def test_a_later_step_does_not_leak_into_an_earlier_arrival(self):
        self.assertFalse(closure({7: [0, 0, 30]}).is_closed(7, 1799))


# O -> A has a fast edge (100 s) and a slow detour through B (500 s + 400 s). A -> D is closed during step 0.
OVERTAKE = Graph(
    [
        Edge(0, 0, 1, 100),
        Edge(1, 0, 3, 500),
        Edge(2, 3, 1, 400),
        Edge(3, 1, 2, 100),
    ]
)


class SearchTest(unittest.TestCase):
    def test_a_later_arrival_passes_a_road_that_was_closed_for_the_earlier_one(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 0, 2, closure({3: [30, 0, 0]}), 0)
        self.assertEqual(result, ArrivalOnlyResult(Route((1, 2, 3), (0, 500, 900), 1000), exact=True))

    def test_the_fast_label_wins_when_nothing_is_closed(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 0, 2, closure({}), 0)
        self.assertEqual(result.route, Route((0, 3), (0, 100), 200))

    def test_origin_is_destination(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 1, 1, closure({}), 250)
        self.assertEqual(result, ArrivalOnlyResult(Route((), (), 250), exact=True))

    def test_unreachable(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 2, 0, closure({}), 0)
        self.assertEqual(result, ArrivalOnlyResult(None, exact=True))

    def test_closed_for_every_arrival(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 0, 2, closure({3: [30, 30, 30]}), 0)
        self.assertEqual(result, ArrivalOnlyResult(None, exact=True))

    def test_a_cycle_terminates_and_stays_exact_when_no_dropped_label_precedes_the_answer(self):
        graph = Graph([Edge(0, 0, 1, 10), Edge(1, 1, 0, 10), Edge(2, 1, 2, 10)])
        result = earliest_arrival_arrival_only(graph, 0, 2, closure({}), 0, max_labels_per_node=3)
        self.assertEqual(result, ArrivalOnlyResult(Route((0, 2), (0, 10), 20), exact=True))

    def test_a_cycle_without_a_destination_terminates(self):
        graph = Graph([Edge(0, 0, 1, 10), Edge(1, 1, 0, 10)])
        result = earliest_arrival_arrival_only(graph, 0, 5, closure({}), 0, max_labels_per_node=4)
        self.assertIsNone(result.route)
        self.assertFalse(result.exact)

    def test_a_dropped_label_earlier_than_the_answer_makes_the_result_inexact(self):
        # The cap of 1 keeps the first arrival at node 1 (10 s), which meets edge 5 closed. The second
        # arrival (1000 s) would pass, but it was dropped.
        graph = Graph([Edge(0, 0, 1, 10), Edge(1, 0, 1, 1000), Edge(5, 1, 2, 10)])
        result = earliest_arrival_arrival_only(graph, 0, 2, closure({5: [30, 0, 0]}), 0, max_labels_per_node=1)
        self.assertEqual(result, ArrivalOnlyResult(None, exact=False))

    def test_a_dropped_label_later_than_the_answer_does_not_matter(self):
        graph = Graph([Edge(0, 0, 1, 10), Edge(1, 0, 1, 1000), Edge(5, 1, 2, 10)])
        result = earliest_arrival_arrival_only(graph, 0, 2, closure({}), 0, max_labels_per_node=1)
        self.assertEqual(result, ArrivalOnlyResult(Route((0, 5), (0, 10), 20), exact=True))


if __name__ == "__main__":
    unittest.main()
