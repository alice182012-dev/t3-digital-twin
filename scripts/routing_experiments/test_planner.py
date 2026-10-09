import unittest

from planner import PlanFailure, PlanRequest, PlannedRoute, http_planner, parse_route_response, route_body
from sampling import Pair

PAIR = Pair("under_2km-0", "under_2km", (105.755, 21.025), (105.762, 21.0255))
REQUEST = PlanRequest(PAIR, "car", "2026-10-08T20:00:00+00:00", "20261009T030000")


def gh_answer(edge_ids, times, distances, hints=None):
    return {"paths": [{"distance": 40.0, "time": 3500, "details": {"edge_id": edge_ids, "time": times, "distance": distances}}],
            "hints": hints or {}}


class ParseTest(unittest.TestCase):
    def test_each_edge_gets_the_time_and_length_of_its_point_interval(self):
        payload = gh_answer([[0, 2, 5], [2, 3, 7]], [[0, 1, 1000], [1, 2, 500], [2, 3, 2000]], [[0, 2, 30.0], [2, 3, 10.0]])
        planned = parse_route_response(200, payload)
        self.assertEqual(planned.route.edge_ids, (5, 7))
        self.assertEqual(planned.route.edge_seconds, (1.5, 2.0))
        self.assertEqual(planned.edge_lengths_m, (30.0, 10.0))
        self.assertEqual(planned.distance_m, 40.0)

    def test_the_engine_hints_are_kept(self):
        payload = gh_answer([[0, 1, 5]], [[0, 1, 1000]], [[0, 1, 9.0]],
                            {"td.status": "applied", "td.run": "20261009T030000", "td.departure": 1791489600, "other": 1})
        self.assertEqual(parse_route_response(200, payload).engine,
                         {"status": "applied", "run": "20261009T030000", "departure": 1791489600})

    def test_cannot_find_point_is_a_drop_and_other_errors_are_not(self):
        drop = parse_route_response(400, {"message": "Cannot find point 1: 21.03,105.76"})
        other = parse_route_response(400, {"message": "Connection between locations not found"})
        self.assertEqual((drop.status, drop.cannot_find_point), (400, True))
        self.assertEqual(other.cannot_find_point, False)

    def test_a_route_with_no_edge_detail_is_a_failure(self):
        failure = parse_route_response(200, {"paths": [{"distance": 0.0, "details": {}}]})
        self.assertIsInstance(failure, PlanFailure)
        self.assertEqual(failure.message, "the route has no edge_id detail")


class RequestTest(unittest.TestCase):
    def test_the_body_asks_for_the_step_and_run_and_the_edge_details(self):
        self.assertEqual(route_body(REQUEST), {
            "points": [[105.755, 21.025], [105.762, 21.0255]], "profile": "car", "points_encoded": False,
            "instructions": False, "details": ["edge_id", "time", "distance"],
            "valid_time": "2026-10-08T20:00:00+00:00", "run": "20261009T030000"})

    def test_the_http_planner_posts_to_route_and_parses_the_answer(self):
        calls = []

        def post(url, body):
            calls.append((url, body["profile"]))
            return 200, gh_answer([[0, 1, 4]], [[0, 1, 2000]], [[0, 1, 12.0]]), 5.0

        planned = http_planner("http://backend:8010", post=post)(REQUEST)
        self.assertEqual(calls, [("http://backend:8010/route", "car")])
        self.assertIsInstance(planned, PlannedRoute)
        self.assertEqual(planned.route.edge_ids, (4,))


if __name__ == "__main__":
    unittest.main()
