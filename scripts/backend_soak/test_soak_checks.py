import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

from soak_checks import (
    VEHICLE_LIMIT_CM,
    dry_shows_promise,
    engine_cell,
    expected_outcome,
    far_point,
    judge_containers,
    judge_vehicle,
    latency_table,
    next_limit_cm,
    percentile,
    pick_roads,
    point_along,
    resolve_run,
    route_passes_through,
    run_logs,
    scan_logs,
    unproven_vehicles,
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


class DryShowsPromiseTest(unittest.TestCase):
    def test_blocked_needs_a_dry_route_that_crosses(self):
        self.assertTrue(dry_shows_promise("blocked", [(True, False), (True, True)]))
        self.assertFalse(dry_shows_promise("blocked", [(True, False), (True, False)]))
        self.assertFalse(dry_shows_promise("blocked", [(False, True), (False, False)]))

    def test_found_needs_only_a_dry_route(self):
        self.assertTrue(dry_shows_promise("found", [(True, False), (False, False)]))
        self.assertFalse(dry_shows_promise("found", [(False, False), (False, False)]))


class UnprovenVehiclesTest(unittest.TestCase):
    def row(self, vehicle, expected, verdict):
        return {"vehicle": vehicle, "expected": expected, "verdict": verdict}

    def test_all_blocked_pairs_skipped_leaves_every_vehicle_with_an_edge_unproven(self):
        rows = [self.row(v, "blocked", "skip") for v in VEHICLE_LIMIT_CM]
        self.assertEqual(unproven_vehicles([45.0], rows), ["motorbike", "car", "truck", "foot"])

    def test_a_judged_blocked_pair_proves_its_vehicle_pass_or_fail(self):
        rows = [self.row("motorbike", "blocked", "pass"), self.row("car", "blocked", "fail"),
                self.row("truck", "blocked", "skip"), self.row("foot", "crosses", "pass")]
        self.assertEqual(unproven_vehicles([45.0], rows), ["truck", "foot"])

    def test_no_edge_at_or_above_a_limit_is_not_a_failure_for_that_vehicle(self):
        self.assertEqual(unproven_vehicles([25.0], [self.row("motorbike", "blocked", "pass")]), [])
        self.assertEqual(unproven_vehicles([25.0], [self.row("motorbike", "blocked", "skip")]), ["motorbike"])
        self.assertEqual(unproven_vehicles([], []), [])


class EngineCellTest(unittest.TestCase):
    STEPS = [datetime(2026, 10, 10, 22, 30), datetime(2026, 10, 10, 22, 45), datetime(2026, 10, 10, 23, 0)]

    @staticmethod
    def hints(moment):
        return {"td.status": "applied", "td.run": "20261010T223000",
                "td.departure": int(moment.replace(tzinfo=timezone.utc).timestamp())}

    def test_a_departure_inside_the_table_floors_to_the_step_at_or_before_it(self):
        self.assertEqual(engine_cell(self.hints(datetime(2026, 10, 10, 22, 50)), self.STEPS),
                         ("20261010T223000", datetime(2026, 10, 10, 22, 45)))

    def test_a_departure_on_a_step_keeps_that_step(self):
        self.assertEqual(engine_cell(self.hints(datetime(2026, 10, 10, 22, 30)), self.STEPS),
                         ("20261010T223000", datetime(2026, 10, 10, 22, 30)))

    def test_a_departure_after_the_table_is_the_last_step(self):
        self.assertEqual(engine_cell(self.hints(datetime(2026, 10, 11, 19, 0)), self.STEPS),
                         ("20261010T223000", datetime(2026, 10, 10, 23, 0)))

    def test_a_departure_before_the_table_is_the_first_step(self):
        self.assertEqual(engine_cell(self.hints(datetime(2026, 10, 10, 12, 0)), self.STEPS),
                         ("20261010T223000", datetime(2026, 10, 10, 22, 30)))

    def test_hints_without_td_run_give_no_cell(self):
        self.assertIsNone(engine_cell({"td.status": "fallback"}, self.STEPS))
        self.assertIsNone(engine_cell({}, self.STEPS))


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


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
import create_edge_depth_tables  # noqa: E402
import create_graph_edge_table  # noqa: E402

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"soak_checks_test_{os.getpid()}"
RUN = "20261010T211500"
VT_UTC = datetime(2026, 10, 10, 14, 15)


def edge_wkt(lon):
    return f"LINESTRING({lon} 21.0, {lon + 0.0005} 21.0)"


@unittest.skipUnless(DSN, "EDGE_DEPTH_TEST_DSN is not set")
class PickRoadsTests(unittest.TestCase):
    """Way 100 has three edges inside the model border, so edge 100:1 is a candidate when its two neighbours are
    wet and low. Way 200 has an edge with no neighbour at all."""

    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute(create_graph_edge_table.SQL)
            cur.execute(create_edge_depth_tables.SQL)
            for edge_id, (key, lon) in enumerate([("100:0", 105.72), ("100:1", 105.7205), ("100:2", 105.721), ("200:0", 105.75)]):
                cur.execute("INSERT INTO graph_edge (edge_id, edge_key, length_m, geom) VALUES (%s, %s, 50, ST_GeomFromText(%s, 4326))",
                            (edge_id, key, edge_wkt(lon)))
            cur.execute("INSERT INTO edge_depth_run (run_ts, graph_hash, valid_times) VALUES (%s, 'h', ARRAY[%s]::timestamp[])",
                        (RUN, VT_UTC))
            cur.execute("INSERT INTO edge_depth VALUES (%s, %s, '100:0', 8), (%s, %s, '100:1', 25), "
                        "(%s, %s, '100:2', 8), (%s, %s, '200:0', 25)", (RUN, VT_UTC) * 4)

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def tearDown(self):
        self.conn.rollback()

    def cursor(self):
        cur = self.conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public")
        return cur

    def test_picks_the_wet_edge_between_two_low_neighbours_in_its_bucket(self):
        with self.cursor() as cur:
            picks = pick_roads(cur, RUN, VT_UTC, per_bucket=3)

        self.assertEqual([(label, key, cm) for label, key, cm, *_ in picks],
                         [("motorbike blocked only", "100:1", 25)])

    def test_a_forecast_time_with_no_wet_edge_gives_no_pick(self):
        with self.cursor() as cur:
            self.assertEqual(pick_roads(cur, RUN, datetime(2026, 10, 10, 15, 0), per_bucket=3), [])

    def test_the_default_is_the_newest_run_and_its_first_step(self):
        with self.cursor() as cur:
            self.assertEqual(resolve_run(cur, None, None), (RUN, VT_UTC))

    def test_a_local_run_timestamp_and_a_local_valid_time_are_converted(self):
        with self.cursor() as cur:
            self.assertEqual(resolve_run(cur, "2026-10-10 21:15:00", "2026-10-10T21:15:00"), (RUN, VT_UTC))
            self.assertEqual(resolve_run(cur, RUN, "2026-10-10T21:15:00+07:00"), (RUN, VT_UTC))


if __name__ == "__main__":
    unittest.main()


DOCKER_500 = "request returned 500 Internal Server Error for API route and version http://docker.example.com/v1.56/containers/json, check if the server supports the requested API version"


def run_logs_on(*texts):
    with tempfile.TemporaryDirectory() as folder:
        paths = []
        for index, text in enumerate(texts):
            path = Path(folder) / f"log{index}.log"
            path.write_text(text)
            paths.append(str(path))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_logs(type("Args", (), {"files": paths})())
    return code, out.getvalue()


class RunLogsTest(unittest.TestCase):
    def test_a_log_of_request_lines_passes(self):
        code, _ = run_logs_on(NGINX_OK + "\n" + PY_OK + "\n")
        self.assertEqual(code, 0)

    def test_an_empty_log_fails_because_no_line_was_read(self):
        code, out = run_logs_on("")
        self.assertEqual(code, 1)
        self.assertIn("no timestamped lines", out)

    def test_a_log_that_holds_only_a_docker_error_fails_and_shows_the_error(self):
        code, out = run_logs_on(DOCKER_500 + "\n")
        self.assertEqual(code, 1)
        self.assertIn("no timestamped lines", out)
        self.assertIn(DOCKER_500[:60], out)

    def test_one_unreadable_log_fails_the_run_even_when_the_others_pass(self):
        code, _ = run_logs_on(NGINX_OK + "\n", "")
        self.assertEqual(code, 1)

    def test_a_5xx_still_fails(self):
        code, _ = run_logs_on(NGINX_502 + "\n")
        self.assertEqual(code, 1)


SINCE = "2026-10-02T00:45:00+07:00"
GH_UP = "/airflow_new-graphhopper-1 started=2026-09-24T03:10:11.123456789Z restarts=0 oomkilled=false status=running"
BACKEND_UP = "/airflow_new-floodmap-backend-1 started=2026-09-30T08:00:00.5Z restarts=0 oomkilled=false status=running"


class JudgeContainersTest(unittest.TestCase):
    def test_containers_started_before_the_window_and_running_have_no_problem(self):
        self.assertEqual(judge_containers([GH_UP, BACKEND_UP], SINCE), [])

    def test_a_container_started_inside_the_window_ends_the_soak(self):
        restarted = "/airflow_new-graphhopper-1 started=2026-10-02T09:00:00.000000000Z restarts=1 oomkilled=false status=running"
        problems = judge_containers([restarted, BACKEND_UP], SINCE)
        self.assertEqual(len(problems), 1)
        self.assertIn("airflow_new-graphhopper-1", problems[0])
        self.assertIn("started inside the window", problems[0])

    def test_start_time_is_compared_as_an_instant_not_as_text(self):
        at_the_start = "/airflow_new-graphhopper-1 started=2026-10-01T17:45:00Z restarts=0 oomkilled=false status=running"
        just_after = "/airflow_new-graphhopper-1 started=2026-10-01T17:45:01Z restarts=0 oomkilled=false status=running"
        self.assertEqual(judge_containers([at_the_start], SINCE), [])
        self.assertEqual(len(judge_containers([just_after], SINCE)), 1)

    def test_an_oom_kill_and_a_stopped_container_are_problems(self):
        oom = "/airflow_new-graphhopper-1 started=2026-09-24T03:10:11Z restarts=0 oomkilled=true status=running"
        stopped = "/airflow_new-floodmap-backend-1 started=2026-09-30T08:00:00Z restarts=0 oomkilled=false status=exited"
        problems = judge_containers([oom, stopped], SINCE)
        self.assertEqual(len(problems), 2)

    def test_no_lines_and_a_docker_error_are_problems_because_nothing_was_read(self):
        self.assertEqual(len(judge_containers([], SINCE)), 1)
        problems = judge_containers([DOCKER_500, GH_UP], SINCE)
        self.assertEqual(len(problems), 1)
        self.assertIn("could not read", problems[0])
