"""Tests for departures.py (US-053): the earliest clear departure of the usual route. No network and no database:

    python test_departures.py
"""
from __future__ import annotations

import copy
import random
import struct
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import departures as dep
import edge_depth_reader as reader

T0 = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
STEP_S = 900
HASH = "a" * 64


def make_table(edges, steps, depth, graph_hash=HASH, run="20261005T170000"):
    """A table in the documented format. steps is a number of 15-minute steps from T0. depth(edge, step) gives centimetres."""
    h, r = graph_hash.encode(), run.encode()
    out = bytearray(struct.pack("<4sHHIHH", b"EDGD", 1, steps, edges, len(h), len(r)) + h + r)
    for i in range(steps):
        out += struct.pack("<q", int(T0.timestamp()) + STEP_S * i)
    for e in range(edges):
        for s in range(steps):
            out += struct.pack("<H", depth(e, s))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.bin"
        path.write_bytes(bytes(out))
        return reader.read_table(path)


def details(edge_ids, millis):
    """GraphHopper path details for a route: one interval per edge, over consecutive point indices."""
    return {
        "edge_id": [[i, i + 1, e] for i, e in enumerate(edge_ids)],
        "time": [[i, i + 1, m] for i, m in enumerate(millis)],
    }


def route_json(edge_ids, millis, hints=None):
    return {"paths": [{"distance": 1000.0 * len(edge_ids), "time": sum(millis), "details": details(edge_ids, millis)}],
            "hints": {"td.graph_hash": HASH, "td.run": "20261005T170000", **(hints or {})}}


def at(minutes):
    return T0 + timedelta(minutes=minutes)


class EntryTimesTest(unittest.TestCase):
    def test_entry_is_the_sum_of_the_times_before_the_edge(self):
        edges, total = dep.entry_offsets(details([7, 8, 9], [60_000, 120_000, 30_000]))
        self.assertEqual(edges, [(7, 0.0), (8, 60.0), (9, 180.0)])
        self.assertEqual(total, 210.0)

    def test_details_that_do_not_line_up_are_refused(self):
        bad = details([1, 2], [1000, 1000])
        bad["time"] = [[0, 2, 2000]]
        with self.assertRaises(ValueError) as caught:
            dep.entry_offsets(bad)
        self.assertIn("line up", str(caught.exception))

    def test_a_route_without_the_details_is_refused(self):
        with self.assertRaises(ValueError):
            dep.entry_offsets({"edge_id": [[0, 1, 5]]})


class CandidatesTest(unittest.TestCase):
    def run_dep(self, table, edges, millis, now, limit=20, vehicle="car"):
        return dep.compute(route_json(edges, millis), table, vehicle=vehicle, limit_cm=limit, now=now)

    def test_a_dry_route_is_clear_at_every_step_and_the_earliest_is_the_first(self):
        table = make_table(3, 8, lambda e, s: 0)
        answer = self.run_dep(table, [0, 1, 2], [60_000] * 3, at(7))
        # Eight steps. A trip that starts at the last step ends after it, so that one is unknown.
        self.assertEqual([c["status"] for c in answer["candidates"]], ["clear"] * 7 + ["unknown"])
        self.assertEqual(answer["earliest_clear"]["departure"], at(0).isoformat())

    def test_candidates_start_at_the_step_that_contains_now(self):
        table = make_table(3, 8, lambda e, s: 0)
        answer = self.run_dep(table, [0], [60_000], at(20))
        self.assertEqual(answer["candidates"][0]["departure"], at(15).isoformat())
        self.assertEqual(len(answer["candidates"]), 7)

    def test_now_before_the_first_step_starts_at_the_first_step(self):
        table = make_table(3, 8, lambda e, s: 0)
        self.assertEqual(self.run_dep(table, [0], [60_000], at(-30))["candidates"][0]["departure"], at(0).isoformat())

    def test_now_after_the_last_step_leaves_only_the_last_step_and_it_is_unknown(self):
        table = make_table(3, 8, lambda e, s: 0)
        answer = self.run_dep(table, [0], [60_000], at(300))
        self.assertEqual([c["status"] for c in answer["candidates"]], ["unknown"])
        self.assertIsNone(answer["earliest_clear"])

    def test_a_road_that_drains_gives_the_first_clear_step(self):
        # Wet at steps 0, 1, 2 (minutes 0, 15, 30). Entered about a minute in, so a departure at step 3 (minute 45) is clear.
        table = make_table(3, 8, lambda e, s: 50 if e == 1 and s <= 2 else 0)
        answer = self.run_dep(table, [0, 1, 2], [60_000] * 3, at(0))
        self.assertEqual([c["status"] for c in answer["candidates"][:5]], ["blocked", "blocked", "blocked", "clear", "clear"])
        self.assertEqual(answer["earliest_clear"]["departure"], at(45).isoformat())

    def test_a_route_blocked_for_the_whole_run_has_no_clear_departure(self):
        table = make_table(3, 8, lambda e, s: 50 if e == 1 else 0)
        answer = self.run_dep(table, [0, 1, 2], [60_000] * 3, at(0))
        self.assertTrue(all(c["status"] == "blocked" for c in answer["candidates"]))
        self.assertIsNone(answer["earliest_clear"])

    def test_a_trip_that_ends_after_the_last_step_is_unknown_when_nothing_closes_it(self):
        table = make_table(2, 8, lambda e, s: 0)
        answer = self.run_dep(table, [0], [90 * 60_000], at(0))  # a 90 minute trip, last step at 105 minutes
        statuses = [c["status"] for c in answer["candidates"]]
        self.assertEqual(statuses[:2], ["clear", "clear"])  # arrival at 90 and 105, known
        self.assertEqual(statuses[2], "unknown")  # departing at 30, arrival at 120
        self.assertEqual(answer["earliest_clear"]["departure"], at(0).isoformat())

    def test_blocked_wins_over_unknown(self):
        table = make_table(2, 8, lambda e, s: 50 if s >= 6 else 0)
        answer = self.run_dep(table, [0, 1], [10 * 60_000, 90 * 60_000], at(0))
        self.assertEqual(answer["candidates"][-1]["status"], "blocked")

    def test_the_margin_end_is_included_and_a_later_step_is_not_counted(self):
        # The edge is entered 20 minutes after departure. Margin 10 minutes: the window ends at minute 30.
        table_at_30 = make_table(2, 8, lambda e, s: 50 if e == 1 and s == 2 else 0)
        self.assertEqual(self.run_dep(table_at_30, [0, 1], [20 * 60_000, 60_000], at(0))["candidates"][0]["status"], "blocked")
        table_at_45 = make_table(2, 8, lambda e, s: 50 if e == 1 and s == 3 else 0)
        self.assertEqual(self.run_dep(table_at_45, [0, 1], [20 * 60_000, 60_000], at(0))["candidates"][0]["status"], "clear")

    def test_a_depth_equal_to_the_limit_closes_the_road(self):
        table = make_table(2, 8, lambda e, s: 20 if e == 1 else 0)
        self.assertEqual(self.run_dep(table, [0, 1], [60_000] * 2, at(0), limit=20)["candidates"][0]["status"], "blocked")
        self.assertEqual(self.run_dep(table, [0, 1], [60_000] * 2, at(0), limit=21)["candidates"][0]["status"], "clear")

    def test_the_limit_decides_the_vehicle(self):
        table = make_table(2, 8, lambda e, s: 25 if e == 1 else 0)
        self.assertEqual(self.run_dep(table, [0, 1], [60_000] * 2, at(0), limit=20, vehicle="motorbike")["earliest_clear"], None)
        self.assertIsNotNone(self.run_dep(table, [0, 1], [60_000] * 2, at(0), limit=30, vehicle="car")["earliest_clear"])

    def test_steps_before_the_departure_are_not_counted(self):
        # Wet only at step 0. A departure at step 1 ignores it.
        table = make_table(2, 8, lambda e, s: 50 if e == 1 and s == 0 else 0)
        answer = self.run_dep(table, [0, 1], [60_000] * 2, at(0))
        self.assertEqual([c["status"] for c in answer["candidates"][:2]], ["blocked", "clear"])

    def test_an_edge_outside_the_table_reads_as_clear(self):
        table = make_table(2, 8, lambda e, s: 50)
        answer = self.run_dep(table, [99], [60_000], at(0))
        self.assertEqual(answer["candidates"][0]["status"], "clear")


class AnswerTest(unittest.TestCase):
    def test_the_answer_names_the_run_its_age_and_the_servers_own_numbers(self):
        table = make_table(3, 8, lambda e, s: 0)
        answer = dep.compute(route_json([0, 1], [60_000, 60_000]), table, vehicle="truck", limit_cm=35, now=at(7))
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["run"], "20261005T170000")
        self.assertEqual(answer["run_age_s"], 7 * 60)
        self.assertEqual(answer["generated_at"], at(7).isoformat())
        self.assertEqual((answer["vehicle"], answer["limit_cm"], answer["margin_s"]), ("truck", 35, 600))
        self.assertEqual(answer["route"], {"distance_m": 2000.0, "time_s": 120.0})

    def test_a_candidate_names_when_to_leave_and_when_the_trip_ends(self):
        table = make_table(3, 8, lambda e, s: 0)
        candidate = dep.compute(route_json([0], [120_000]), table, vehicle="car", limit_cm=30, now=at(7))["candidates"][0]
        self.assertEqual(candidate["departure"], at(0).isoformat())
        self.assertEqual(candidate["leave_at"], at(7).isoformat(), "nobody leaves in the past")
        self.assertEqual(candidate["arrival"], (at(7) + timedelta(seconds=120)).isoformat(), "from when the traveller leaves")
        self.assertEqual(dep.compute(route_json([0], [60_000]), table, vehicle="car", limit_cm=30, now=at(7))["candidates"][1]["leave_at"], at(15).isoformat())

    def test_an_unavailable_answer_carries_the_reason(self):
        answer = dep.unavailable("no table has been published in /tables", "car", at(7))
        self.assertEqual(answer["status"], "unavailable")
        self.assertIn("/tables", answer["reason"])
        self.assertEqual(answer["candidates"], [])
        self.assertIsNone(answer["earliest_clear"])


class RequestTest(unittest.TestCase):
    BODY = {"points": [[105.75, 21.0], [105.756, 21.0]], "profile": "car"}

    def test_the_route_body_has_the_details_and_no_flood_model_and_no_search(self):
        out = dep.usual_route_body({**self.BODY, "custom_model": {"x": 1}, "valid_time": "2026-10-05T10:00:00Z", "ch.disable": False, "td_departure": 5})
        self.assertEqual(out["details"], ["edge_id", "time"])
        self.assertIs(out["points_encoded"], False)
        self.assertIs(out["td_info"], True)
        for key in ("custom_model", "valid_time", "ch.disable", "td_departure"):
            self.assertNotIn(key, out)
        self.assertEqual(out["points"], self.BODY["points"])
        self.assertEqual(out["profile"], "car")

    def test_the_client_cannot_pick_the_clock_the_margin_or_the_policy(self):
        parsed = dep.parse_request({**self.BODY, "now": "2030-01-01T00:00:00Z", "margin_s": 0, "margin": 0, "limit_cm": 999, "policy": "x"})
        self.assertEqual(set(parsed), {"points", "profile"})

    def test_a_request_needs_two_points_and_a_known_profile(self):
        for bad in ({"profile": "car"}, {"points": [[1, 2]], "profile": "car"}, {"points": self.BODY["points"]},
                    {"points": self.BODY["points"], "profile": "tank"}):
            with self.assertRaises(ValueError):
                dep.parse_request(bad)

    def test_a_point_that_is_not_a_pair_of_numbers_is_refused(self):
        with self.assertRaises(ValueError):
            dep.parse_request({"points": [[1, 2], ["a", "b"]], "profile": "car"})


class FlowTest(unittest.TestCase):
    """departures_request with GraphHopper and the table passed in."""

    BODY = {"points": [[105.75, 21.0], [105.756, 21.0]], "profile": "car"}

    def flow(self, post_answer, table_or_error, now=at(7), limit=30):
        posted = []

        def post(body):
            posted.append(copy.deepcopy(body))
            return post_answer

        def load():
            if isinstance(table_or_error, Exception):
                raise table_or_error
            return table_or_error

        outcome = dep.departures_request(copy.deepcopy(self.BODY), post=post, load_table=load, limit_for=lambda p: limit, now=now)
        return outcome, posted

    def ok(self, **kw):
        return {"ok": True, "status": 200, "json": route_json([0, 1], [60_000, 60_000], **kw)}

    def test_a_good_request_returns_the_answer(self):
        table = make_table(3, 8, lambda e, s: 0)
        outcome, posted = self.flow(self.ok(), table)
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.data["status"], "ok")
        self.assertEqual(posted[0]["details"], ["edge_id", "time"])

    def test_no_route_passes_the_graphhopper_error_through(self):
        outcome, _ = self.flow({"ok": False, "status": 400, "error": '{"message": "Connection between locations not found"}'}, make_table(3, 8, lambda e, s: 0))
        self.assertEqual(outcome, dep.Outcome(False, 400, '{"message": "Connection between locations not found"}'))

    def test_a_missing_table_is_unavailable_not_an_error(self):
        outcome, _ = self.flow(self.ok(), reader.TableUnavailable("no table has been published in /tables"))
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.data["status"], "unavailable")
        self.assertIn("no table has been published", outcome.data["reason"])

    def test_a_table_for_another_graph_is_unavailable_and_names_both_hashes(self):
        table = make_table(3, 8, lambda e, s: 0, graph_hash="b" * 64)
        outcome, _ = self.flow(self.ok(), table)
        self.assertEqual(outcome.data["status"], "unavailable")
        self.assertIn("b" * 64, outcome.data["reason"])
        self.assertIn(HASH, outcome.data["reason"])

    def test_a_graphhopper_that_does_not_report_its_hash_is_unavailable(self):
        response = self.ok()
        del response["json"]["hints"]["td.graph_hash"]
        outcome, _ = self.flow(response, make_table(3, 8, lambda e, s: 0))
        self.assertEqual(outcome.data["status"], "unavailable")
        self.assertIn("graph hash", outcome.data["reason"])

    def test_details_that_do_not_line_up_are_an_error_not_a_guess(self):
        response = self.ok()
        response["json"]["paths"][0]["details"]["time"] = [[0, 2, 120000]]
        with self.assertRaises(ValueError):
            self.flow(response, make_table(3, 8, lambda e, s: 0))


class ReferenceTest(unittest.TestCase):
    """The same rule as scripts/routing_reference/sticky_reference.py, on random routes and tables."""

    REFERENCE = Path(__file__).resolve().parents[3] / "scripts" / "routing_reference"

    @unittest.skipUnless((REFERENCE / "sticky_reference.py").exists(), "scripts/routing_reference is not in this build context")
    def test_every_candidate_matches_the_reference_rule(self):
        sys.path.insert(0, str(self.REFERENCE))
        import sticky_reference as ref

        rnd = random.Random(7)
        blocked = clear = 0
        for case in range(300):
            edges = rnd.randint(1, 6)
            wet = {(e, s): rnd.random() < 0.18 for e in range(edges) for s in range(8)}
            table = make_table(edges, 8, lambda e, s: 40 if wet[(e, s)] else 0)
            millis = [rnd.randint(1, 20) * 60_000 for _ in range(edges)]
            limit = 20
            answer = dep.compute(route_json(list(range(edges)), millis), table, vehicle="car", limit_cm=limit, now=at(0))
            steps = tuple(t.timestamp() for t in table.step_times)
            for candidate in answer["candidates"]:
                d = datetime.fromisoformat(candidate["departure"]).timestamp()
                rule = ref.StickyClosure(steps, lambda e, s: table.depth_cm(e, s), limit, departure_s=d, margin_s=600)
                crossings = ref.find_crossings(list(range(edges)), [m / 1000 for m in millis], rule)
                if crossings:
                    self.assertEqual(candidate["status"], "blocked", f"case {case} {candidate}")
                    blocked += 1
                else:
                    self.assertIn(candidate["status"], ("clear", "unknown"), f"case {case} {candidate}")
                    clear += 1
        self.assertTrue(blocked > 100 and clear > 100, (blocked, clear))


if __name__ == "__main__":
    unittest.main()
