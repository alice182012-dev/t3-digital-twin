import json
import struct
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import routing_proof as rp

T0 = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


def make_table(directory, edges, steps, depth, run="20261005T170000", graph_hash="a" * 64):
    h, r = graph_hash.encode(), run.encode()
    out = bytearray(struct.pack("<4sHHIHH", b"EDGD", 1, steps, edges, len(h), len(r)) + h + r)
    for i in range(steps):
        out += struct.pack("<q", int(T0.timestamp()) + 900 * i)
    for e in range(edges):
        for s in range(steps):
            out += struct.pack("<H", depth(e, s))
    path = Path(directory) / f"{run}.bin"
    path.write_bytes(bytes(out))
    return path


def result(name, edges, vehicle="car", distance=None, td=None, status=200, millis=None, at=T0):
    return {
        "name": name, "vehicle": vehicle, "from": [105.75, 21.0], "to": [105.76, 21.0], "requested_at": at.timestamp(),
        "status": status, "distance": distance if distance is not None else 1000.0 * len(edges),
        "time_ms": sum(millis or [60000] * len(edges)), "edge_ids": edges, "edge_times_ms": millis or [60000] * len(edges),
        "td": td or {},
    }


class BaselineTest(unittest.TestCase):
    def test_the_constants_equal_the_table_in_the_vault(self):
        md = ROOT / "artifacts" / "docs" / "blockers" / "routing-not-time-aware.md"
        if not md.exists():
            self.skipTest("the vault is not in this checkout")
        text = md.read_text(encoding="utf-8")
        self.assertEqual(rp.parse_baseline(text, "C. `floodmap-backend`, areas cached"), rp.BASELINE_C)
        self.assertEqual(rp.parse_baseline(text, "B. GraphHopper, flood model of the run"), rp.BASELINE_B)

    def test_parse_reads_both_vehicles_and_all_trips(self):
        text = "| C. x | short | 1.5 / 2.5 | 3 / 4 |\n| C. x | long | 1,000 / 2,000 | 5 / 6 |\n| D. y | short | 9 / 9 | 9 / 9 |"
        self.assertEqual(
            rp.parse_baseline(text, "C. x"),
            {("short", "motorbike"): (1.5, 2.5), ("short", "car"): (3.0, 4.0), ("long", "motorbike"): (1000.0, 2000.0), ("long", "car"): (5.0, 6.0)},
        )


class LatencyTest(unittest.TestCase):
    BASE = {("short", "car"): (100.0, 200.0), ("long", "car"): (1000.0, 2000.0)}

    def cell(self, p50, p95, statuses=None, td=None):
        return {"p50_ms": p50, "p95_ms": p95, "statuses": statuses or {"200": 30}, "td_statuses": td or {"applied": 30}}

    def test_a_cell_within_the_factor_passes(self):
        verdict = rp.judge_latency({("short", "car"): self.cell(200.0, 400.0)}, self.BASE, 2.0)
        self.assertTrue(verdict.passed)
        self.assertTrue(verdict.cells[0].ok)

    def test_the_factor_is_inclusive_and_either_percentile_can_fail_it(self):
        self.assertTrue(rp.judge_latency({("short", "car"): self.cell(200.0, 400.0)}, self.BASE, 2.0).passed)
        self.assertFalse(rp.judge_latency({("short", "car"): self.cell(200.1, 400.0)}, self.BASE, 2.0).passed)
        self.assertFalse(rp.judge_latency({("short", "car"): self.cell(150.0, 400.1)}, self.BASE, 2.0).passed)

    def test_a_request_that_did_not_return_200_fails_the_cell(self):
        self.assertFalse(rp.judge_latency({("short", "car"): self.cell(10.0, 20.0, {"200": 29, "400": 1})}, self.BASE, 2.0).passed)

    def test_a_fallback_fails_the_cell_because_the_engine_did_not_run(self):
        self.assertFalse(rp.judge_latency({("short", "car"): self.cell(10.0, 20.0, td={"applied": 29, "fallback": 1})}, self.BASE, 2.0).passed)

    def test_unknown_is_a_known_answer_and_passes(self):
        self.assertTrue(rp.judge_latency({("short", "car"): self.cell(10.0, 20.0, td={"applied": 15, "unknown": 15})}, self.BASE, 2.0).passed)

    def test_a_cell_with_no_baseline_fails_rather_than_passes_silently(self):
        self.assertFalse(rp.judge_latency({("medium", "car"): self.cell(10.0, 20.0)}, self.BASE, 2.0).passed)

    def test_nothing_measured_is_not_a_pass(self):
        self.assertFalse(rp.judge_latency({}, self.BASE, 2.0).passed)

    def test_the_table_names_each_cell_and_the_verdict(self):
        text = rp.render_latency(rp.judge_latency({("short", "car"): self.cell(250.0, 400.0)}, self.BASE, 2.0))
        self.assertIn("short", text)
        self.assertIn("OVER", text)
        self.assertIn("FAIL", text)


class CompareTest(unittest.TestCase):
    def td(self, status="applied"):
        return {"status": status, "run": "20261005T170000"}

    def test_the_share_of_routes_that_change_and_the_median_detour_ratio(self):
        a = [result("p1", [1, 2, 3], distance=1000), result("p2", [4, 5], distance=2000), result("p3", [6], distance=500), result("p4", [7], distance=800)]
        b = [result("p1", [1, 9, 3], distance=1500, td=self.td()), result("p2", [4, 5], distance=2000, td=self.td()),
             result("p3", [6, 8], distance=1000, td=self.td()), result("p4", [7], distance=800, td=self.td())]
        out = rp.compare_runs(a, b)
        self.assertEqual((out["compared"], out["changed"]), (4, 2))
        self.assertAlmostEqual(out["percent_changed"], 50.0)
        self.assertAlmostEqual(out["median_detour_ratio"], 1.75)  # ratios 1.5 and 2.0

    def test_a_pair_without_a_route_in_either_run_is_listed_and_not_counted(self):
        a = [result("p1", [1], distance=100), result("p2", [], status=400)]
        b = [result("p1", [1], distance=100, td=self.td()), result("p2", [2], distance=100, td=self.td()), result("p3", [], status=400, td=self.td())]
        out = rp.compare_runs(a, b)
        self.assertEqual(out["compared"], 1)
        self.assertEqual(sorted(out["not_compared"]), ["p2", "p3"])

    def test_the_engine_statuses_are_counted_and_a_fallback_fails(self):
        a = [result("p1", [1]), result("p2", [2])]
        b = [result("p1", [1], td=self.td()), result("p2", [2], td=self.td("fallback"))]
        out = rp.compare_runs(a, b)
        self.assertEqual(out["engine_statuses"], {"applied": 1, "fallback": 1})
        self.assertFalse(out["engine_ok"])

    def test_no_change_gives_zero_percent_and_no_ratio(self):
        a = [result("p1", [1])]
        b = [result("p1", [1], td=self.td())]
        out = rp.compare_runs(a, b)
        self.assertEqual((out["changed"], out["percent_changed"], out["median_detour_ratio"]), (0, 0.0, None))

    def test_a_pair_is_matched_by_name_and_vehicle(self):
        a = [result("p1", [1], vehicle="car"), result("p1", [2], vehicle="foot")]
        b = [result("p1", [1], vehicle="car", td=self.td()), result("p1", [3], vehicle="foot", td=self.td())]
        out = rp.compare_runs(a, b)
        self.assertEqual((out["compared"], out["changed"]), (2, 1))


class CrossingsTest(unittest.TestCase):
    def td(self, departure):
        return {"status": "applied", "run": "20261005T170000", "departure": departure}

    def test_a_route_the_engine_made_over_a_closed_road_is_a_crossing(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_table(tmp, 4, 8, lambda e, s: 50 if e == 1 else 0)
            b = [result("p1", [0, 1, 2], td=self.td(int(T0.timestamp())))]
            found = rp.check_crossings(b, Path(tmp), limits={"car": 30}, margin_s=600)
        self.assertEqual(len(found["p1|car"]), 1)
        self.assertEqual(found["p1|car"][0]["edge_id"], 1)

    def test_a_route_around_the_closed_road_has_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_table(tmp, 4, 8, lambda e, s: 50 if e == 1 else 0)
            b = [result("p1", [0, 3, 2], td=self.td(int(T0.timestamp())))]
            found = rp.check_crossings(b, Path(tmp), limits={"car": 30}, margin_s=600)
        self.assertEqual(found["p1|car"], [])

    def test_the_limit_of_the_vehicle_decides(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_table(tmp, 4, 8, lambda e, s: 25 if e == 1 else 0)
            b = [result("p1", [0, 1], vehicle="motorbike", td=self.td(int(T0.timestamp()))), result("p2", [0, 1], vehicle="car", td=self.td(int(T0.timestamp())))]
            found = rp.check_crossings(b, Path(tmp), limits={"motorbike": 20, "car": 30}, margin_s=600)
        self.assertEqual((len(found["p1|motorbike"]), len(found["p2|car"])), (1, 0))

    def test_a_run_without_an_engine_departure_is_judged_from_the_step_that_contains_the_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_table(tmp, 4, 8, lambda e, s: 50 if e == 1 and s == 0 else 0)
            (Path(tmp) / "latest").write_text("20261005T170000.bin\n")
            a = [result("p1", [0, 1], at=T0 + timedelta(minutes=7))]  # the step at 0 contains minute 7
            found = rp.check_crossings(a, Path(tmp), limits={"car": 30}, margin_s=600)
        self.assertEqual(len(found["p1|car"]), 1)

    def test_the_route_is_walked_from_the_time_of_the_request_not_from_the_floored_step(self):
        # Wet from the step at 1,800 s. Requested at 840 s, floored to 0 s, the road entered 1,000 s into the trip.
        with tempfile.TemporaryDirectory() as tmp:
            make_table(tmp, 4, 8, lambda e, s: 50 if e == 1 and s >= 2 else 0)
            b = [result("p1", [0, 1], millis=[1_000_000, 60_000], td=self.td(int(T0.timestamp())), at=T0 + timedelta(seconds=840))]
            found = rp.check_crossings(b, Path(tmp), limits={"car": 30}, margin_s=600)
        self.assertEqual(found["p1|car"], [{"position": 1, "edge_id": 1, "arrival_s": T0.timestamp() + 1840, "closing_step": 2}])

    def test_a_request_exactly_on_a_step_is_walked_from_that_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_table(tmp, 4, 8, lambda e, s: 50 if e == 1 and s >= 2 else 0)
            on_step = int(T0.timestamp()) + 900
            b = [result("p1", [0, 1], millis=[1_000_000, 60_000], td=self.td(on_step), at=T0 + timedelta(seconds=900))]
            found = rp.check_crossings(b, Path(tmp), limits={"car": 30}, margin_s=600)
        self.assertEqual(found["p1|car"], [{"position": 1, "edge_id": 1, "arrival_s": T0.timestamp() + 1900, "closing_step": 2}])

    def test_a_pair_with_no_route_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_table(tmp, 4, 8, lambda e, s: 0)
            found = rp.check_crossings([result("p1", [], status=400)], Path(tmp), limits={"car": 30}, margin_s=600)
        self.assertEqual(found, {})

    def test_the_table_of_the_run_the_engine_named_is_the_one_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_table(tmp, 4, 8, lambda e, s: 50 if e == 1 else 0, run="20261005T170000")
            make_table(tmp, 4, 8, lambda e, s: 0, run="20261005T171500")
            (Path(tmp) / "latest").write_text("20261005T171500.bin\n")
            td = {"status": "applied", "run": "20261005T170000", "departure": int(T0.timestamp())}
            found = rp.check_crossings([result("p1", [0, 1], td=td)], Path(tmp), limits={"car": 30}, margin_s=600)
        self.assertEqual(len(found["p1|car"]), 1, "the pinned run, not the newest")


class PairsAndBodyTest(unittest.TestCase):
    def test_the_pairs_file_has_the_three_trips_for_all_four_vehicles_inside_the_border(self):
        pairs = json.loads((Path(__file__).parent / "pairs.json").read_text())
        names = {(p["name"], p["vehicle"]) for p in pairs}
        for trip in ("short", "medium", "long"):
            for vehicle in ("motorbike", "car", "truck", "foot"):
                self.assertIn((trip, vehicle), names)
        for pair in pairs:
            for lon, lat in (pair["from"], pair["to"]):
                self.assertTrue(105.7015 <= lon <= 105.7971 and 20.9754 <= lat <= 21.0269, pair)

    def test_the_request_body_has_the_details_and_the_flood_step(self):
        body = rp.route_body({"name": "short", "vehicle": "car", "from": [105.755, 21.025], "to": [105.762, 21.0255]},
                             {"valid_time": "2026-10-05T17:15:00+07:00", "run": "20261005T170000"})
        self.assertEqual(body["points"], [[105.755, 21.025], [105.762, 21.0255]])
        self.assertEqual(body["profile"], "car")
        self.assertEqual(body["details"], ["edge_id", "time"])
        self.assertEqual((body["valid_time"], body["run"]), ("2026-10-05T17:15:00+07:00", "20261005T170000"))
        for key in ("td_departure", "custom_model"):
            self.assertNotIn(key, body)

    def test_the_current_step_is_the_latest_at_or_before_now_and_the_earliest_when_all_are_ahead(self):
        steps = [{"valid_time": (T0 + timedelta(minutes=15 * i)).isoformat(), "run": "r"} for i in range(4)]
        self.assertEqual(rp.current_step(steps, T0 + timedelta(minutes=20))["valid_time"], steps[1]["valid_time"])
        self.assertEqual(rp.current_step(steps, T0 - timedelta(hours=1))["valid_time"], steps[0]["valid_time"])
        self.assertEqual(rp.current_step(steps, T0 + timedelta(days=1))["valid_time"], steps[3]["valid_time"])
        with self.assertRaises(ValueError):
            rp.current_step([], T0)

    def test_a_record_is_made_from_a_backend_answer(self):
        payload = {"paths": [{"distance": 1234.5, "time": 90000, "details": {"edge_id": [[0, 1, 7], [1, 2, 8]], "time": [[0, 1, 40000], [1, 2, 50000]]}}],
                   "hints": {"td.status": "applied", "td.run": "20261005T170000", "td.departure": 1790000000}}
        rec = rp.make_record({"name": "short", "vehicle": "car", "from": [1, 2], "to": [3, 4]}, 200, payload, T0)
        self.assertEqual((rec["edge_ids"], rec["edge_times_ms"], rec["distance"]), ([7, 8], [40000, 50000], 1234.5))
        self.assertEqual(rec["td"], {"status": "applied", "run": "20261005T170000", "departure": 1790000000})
        none = rp.make_record({"name": "short", "vehicle": "car", "from": [1, 2], "to": [3, 4]}, 400, {"message": "Connection between locations not found"}, T0)
        self.assertEqual((none["status"], none["edge_ids"]), (400, []))
        self.assertIn("Connection", none["message"])


if __name__ == "__main__":
    unittest.main()
