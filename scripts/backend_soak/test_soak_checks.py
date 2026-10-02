import unittest

from soak_checks import (
    VEHICLE_LIMIT_CM,
    expected_outcome,
    far_point,
    judge_vehicle,
    latency_table,
    next_limit_cm,
    percentile,
    point_along,
    route_passes_through,
    scan_logs,
)

NGINX_OK = '2026-10-01T19:16:32.426645197Z 172.18.0.1 - - [01/Oct/2026:19:16:32 +0000] "POST /api/gh/route?key= HTTP/1.1" 200 2096 "-" "UA"'
NGINX_400 = '2026-10-01T19:16:32.674970971Z 172.18.0.1 - - [01/Oct/2026:19:16:32 +0000] "POST /api/gh/route?key= HTTP/1.1" 400 193 "-" "UA"'
NGINX_502 = '2026-10-01T19:20:00.000000000Z 172.18.0.1 - - [01/Oct/2026:19:20:00 +0000] "POST /api/gh/route?key= HTTP/1.1" 502 150 "-" "UA"'
PY_OK = '2026-10-01T19:11:30.836746011Z 172.18.0.11 - - [01/Oct/2026 19:11:30] "GET /flood/timesteps HTTP/1.1" 200 -'
PY_500 = '2026-10-01T19:12:00.000000000Z 172.18.0.11 - - [01/Oct/2026 19:12:00] "POST /route?key= HTTP/1.1" 500 -'
GH_INFO = '2026-10-01T18:46:25.612248774Z INFO  [2026-10-01 18:46:25,603] com.graphhopper.http.MultiExceptionMapper: bad request: [com.graphhopper.util.exceptions.ConnectionNotFoundException: Connection between locations not found]'
GH_ERROR = '2026-10-01T19:30:00.000000000Z ERROR [2026-10-01 19:30:00,000] com.graphhopper.resources.RouteResource: boom'
GH_TRACE = '2026-10-01T19:30:00.100000000Z java.lang.OutOfMemoryError: Java heap space'


class ScanLogsTest(unittest.TestCase):
    def test_counts_each_status_class_and_lists_the_5xx_lines(self):
        report = scan_logs([NGINX_OK, NGINX_400, NGINX_502, PY_OK, PY_500])
        self.assertEqual(report.requests, 5)
        self.assertEqual(report.by_status, {200: 2, 400: 1, 502: 1, 500: 1})
        self.assertEqual(report.server_errors, [NGINX_502, PY_500])

    def test_a_400_is_a_client_error_and_never_a_server_error(self):
        report = scan_logs([NGINX_400, GH_INFO])
        self.assertEqual(report.server_errors, [])
        self.assertEqual(report.error_lines, [])

    def test_graphhopper_error_level_and_exception_traces_are_error_lines(self):
        report = scan_logs([GH_INFO, GH_ERROR, GH_TRACE])
        self.assertEqual(report.error_lines, [GH_ERROR, GH_TRACE])
        self.assertEqual(report.requests, 0)

    def test_a_connection_not_found_info_line_is_counted_as_a_bad_request_only(self):
        report = scan_logs([GH_INFO])
        self.assertEqual(report.bad_requests, 1)

    def test_first_and_last_timestamps_come_from_the_docker_prefix(self):
        report = scan_logs([PY_OK, NGINX_502])
        self.assertEqual(report.first, "2026-10-01T19:11:30.836746011Z")
        self.assertEqual(report.last, "2026-10-01T19:20:00.000000000Z")

    def test_empty_input_has_no_window(self):
        report = scan_logs([])
        self.assertEqual((report.requests, report.first, report.last), (0, None, None))


class PercentileTest(unittest.TestCase):
    def test_nearest_rank_on_100_values(self):
        values = list(range(1, 101))
        self.assertEqual(percentile(values, 50), 50)
        self.assertEqual(percentile(values, 95), 95)

    def test_unsorted_input_and_a_single_value(self):
        self.assertEqual(percentile([9, 1, 5], 50), 5)
        self.assertEqual(percentile([7], 95), 7)


class ExpectedOutcomeTest(unittest.TestCase):
    def test_limits_are_the_documented_ones(self):
        self.assertEqual(VEHICLE_LIMIT_CM, {"motorbike": 20, "car": 30, "truck": 35, "foot": 40})

    def test_at_or_past_the_limit_is_blocked_because_band_b4_starts_at_the_limit(self):
        self.assertEqual(expected_outcome(20.0, "motorbike"), "blocked")
        self.assertEqual(expected_outcome(25.0, "motorbike"), "blocked")
        self.assertEqual(expected_outcome(80.0, "foot"), "blocked")

    def test_a_vehicle_with_a_higher_limit_than_the_depth_is_not_blocked(self):
        self.assertNotEqual(expected_outcome(25.0, "car"), "blocked")
        self.assertNotEqual(expected_outcome(37.0, "foot"), "blocked")

    def test_from_half_the_limit_the_road_is_penalised_so_a_route_only_has_to_exist(self):
        self.assertEqual(expected_outcome(15.0, "car"), "found")
        self.assertEqual(expected_outcome(29.0, "car"), "found")

    def test_below_half_the_limit_the_route_has_to_cross_the_road(self):
        self.assertEqual(expected_outcome(14.9, "car"), "crosses")
        self.assertEqual(expected_outcome(5.0, "foot"), "crosses")

    def test_next_limit_is_the_smallest_limit_above_the_depth(self):
        self.assertEqual(next_limit_cm(25.0), 30)
        self.assertEqual(next_limit_cm(36.0), 40)
        self.assertIsNone(next_limit_cm(45.0))


class RoutePassesThroughTest(unittest.TestCase):
    ROUTE = [(105.7590, 21.0000), (105.7600, 21.0000), (105.7610, 21.0000)]  # about 105 m, east to west

    def test_a_route_that_runs_over_both_points_passes_through_them(self):
        points = [(105.7595, 21.0000), (105.7605, 21.0000)]
        self.assertTrue(route_passes_through(self.ROUTE, points, tol_m=6))

    def test_a_route_that_misses_one_point_does_not(self):
        points = [(105.7595, 21.0000), (105.7605, 21.0010)]
        self.assertFalse(route_passes_through(self.ROUTE, points, tol_m=6))

    def test_an_empty_route_passes_through_nothing(self):
        self.assertFalse(route_passes_through([], [(105.7595, 21.0000)], tol_m=6))


class PointAlongTest(unittest.TestCase):
    def test_a_fraction_of_a_bent_line_is_measured_by_length_not_by_vertex_count(self):
        piece = [(105.7600, 21.0000), (105.7600, 21.0004), (105.7612, 21.0004)]
        lon, lat = point_along(piece, 0.5)
        self.assertAlmostEqual(lat, 21.0004, places=6)
        self.assertGreater(lon, 105.7600)

    def test_fraction_zero_and_one_are_the_ends(self):
        piece = [(105.7600, 21.0000), (105.7604, 21.0000)]
        self.assertEqual(point_along(piece, 0.0), piece[0])
        self.assertEqual(point_along(piece, 1.0), piece[1])


class FarPointTest(unittest.TestCase):
    PIECE = [(105.7600, 21.0000), (105.7604, 21.0000)]

    def test_picks_the_point_near_the_far_end_of_a_neighbour_whichever_way_it_is_stored(self):
        east = [(105.7604, 21.0000), (105.7609, 21.0000)]
        for neighbour in (east, east[::-1]):
            lon, lat = far_point(neighbour, self.PIECE)
            self.assertGreater(lon, 105.7608)
            self.assertAlmostEqual(lat, 21.0000, places=6)


class JudgeVehicleTest(unittest.TestCase):
    """Each direction is (route_found, route_crosses_piece). The control is the same pair with no flood model."""

    DRY_CROSSES = [(True, True), (True, True)]
    DRY_DETOURS = [(True, False), (True, False)]
    DRY_NONE = [(False, False), (False, False)]

    def test_blocked_with_no_route_either_way_passes(self):
        self.assertEqual(judge_vehicle("blocked", [(False, False), (False, False)], self.DRY_CROSSES), "pass")

    def test_blocked_with_a_detour_that_avoids_the_piece_passes(self):
        self.assertEqual(judge_vehicle("blocked", [(True, False), (True, False)], self.DRY_CROSSES), "pass")

    def test_blocked_but_routed_across_the_piece_fails(self):
        self.assertEqual(judge_vehicle("blocked", [(False, False), (True, True)], self.DRY_CROSSES), "fail")

    def test_blocked_is_skipped_when_even_the_dry_route_does_not_cross_the_piece(self):
        self.assertEqual(judge_vehicle("blocked", [(True, False), (True, False)], self.DRY_DETOURS), "skip")

    def test_found_passes_with_a_detour_and_fails_with_no_route(self):
        self.assertEqual(judge_vehicle("found", [(True, False), (False, False)], self.DRY_CROSSES), "pass")
        self.assertEqual(judge_vehicle("found", [(False, False), (False, False)], self.DRY_CROSSES), "fail")

    def test_found_is_skipped_when_the_dry_route_is_not_found_either(self):
        self.assertEqual(judge_vehicle("found", [(False, False), (False, False)], self.DRY_NONE), "skip")

    def test_crosses_needs_a_route_over_the_piece_in_at_least_one_direction(self):
        self.assertEqual(judge_vehicle("crosses", [(False, False), (True, True)], self.DRY_CROSSES), "pass")
        self.assertEqual(judge_vehicle("crosses", [(True, False), (True, False)], self.DRY_CROSSES), "fail")

    def test_crosses_is_skipped_when_the_dry_route_does_not_cross(self):
        self.assertEqual(judge_vehicle("crosses", [(True, False), (True, False)], self.DRY_DETOURS), "skip")


class LatencyTableTest(unittest.TestCase):
    DATA = {
        "results": {
            "A graphhopper | short | motorbike": {"p50_ms": 11.2, "p95_ms": 18.3, "statuses": {"200": 30}, "road_distance_m": 1906},
            "A graphhopper | short | car": {"p50_ms": 8.0, "p95_ms": 13.9, "statuses": {"200": 30}, "road_distance_m": 1906},
            "C backend | short | motorbike": {"p50_ms": 136.5, "p95_ms": 157.6, "statuses": {"200": 29, "400": 1}, "road_distance_m": 1906},
        }
    }

    def test_one_row_per_target_and_trip_with_a_p50_and_p95_for_each_vehicle(self):
        self.assertEqual(
            latency_table(self.DATA).splitlines(),
            [
                "target                 trip     motorbike p50/p95 ms   car p50/p95 ms   road m",
                "A graphhopper          short    11.2 / 18.3            8.0 / 13.9       1906",
                "C backend              short    136.5 / 157.6 (!)      -                1906",
            ],
        )


if __name__ == "__main__":
    unittest.main()
