"""Tests for time_aware_route.py (US-052). No network, no database, and no import of server.py:

    python test_time_aware_route.py
"""
from __future__ import annotations

import copy
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import time_aware_route as tar

NOW = datetime(2026, 10, 5, 10, 7, 30, tzinfo=timezone.utc)
NOW_EPOCH = int(NOW.timestamp())
ROUTE = {"paths": [{"distance": 600.0, "time": 90000, "points": "stub"}], "hints": {"visited_nodes.sum": 10}}
CUSTOM_MODEL = {"priority": [{"if": "in_flood", "multiply_by": "0"}]}


class FakePost:
    """Stands in for post_graphhopper_route. It answers from a list and records the bodies it was given."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.bodies = []

    def __call__(self, body):
        self.bodies.append(copy.deepcopy(body))
        return copy.deepcopy(self.answers.pop(0))


def ok(extra_hints=None, status=200):
    data = copy.deepcopy(ROUTE)
    data["hints"].update(extra_hints or {})
    return {"ok": True, "status": status, "json": data}


def error(status=400, text='{"message": "Connection between locations not found"}'):
    return {"ok": False, "status": status, "error": text}


def areas(calls):
    def fn(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2):
        calls.append((valid_time, vehicle_type, run))
        return CUSTOM_MODEL

    return fn


def request(**extra):
    body = {"points": [[105.75, 21.0], [105.756, 21.0]], "profile": "car", "points_encoded": False,
            "valid_time": "2026-10-05T10:00:00+00:00", "run": "latest"}
    body.update(extra)
    return body


def today_body(body, with_areas=True):
    """What the backend sends today (before this story): the client's fields, minus the flood fields, plus the areas."""
    out = {k: v for k, v in body.items() if k not in ("valid_time", "run", "vehicle_type", "buffer", "simplify", "min_area")}
    if with_areas and body.get("valid_time"):
        out["ch.disable"] = True
        out["custom_model"] = CUSTOM_MODEL
    return out


class FlagTest(unittest.TestCase):
    def test_the_flag_reads_common_spellings(self):
        for text in ("1", "true", "TRUE", "yes", "on", " On "):
            self.assertTrue(tar.flag_enabled({"TIME_AWARE_ROUTING": text}), text)
        for text in ("", "0", "false", "off", "no", "banana"):
            self.assertFalse(tar.flag_enabled({"TIME_AWARE_ROUTING": text}), text)

    def test_the_flag_is_off_when_unset(self):
        self.assertFalse(tar.flag_enabled({}))


class DepartureTest(unittest.TestCase):
    def test_a_valid_time_in_the_past_gives_now(self):
        self.assertEqual(tar.departure_epoch("2026-10-05T09:00:00+00:00", NOW), NOW_EPOCH)

    def test_a_valid_time_in_the_future_is_kept(self):
        later = NOW + timedelta(minutes=30)
        self.assertEqual(tar.departure_epoch(later.isoformat(), NOW), int(later.timestamp()))

    def test_no_valid_time_gives_now(self):
        self.assertEqual(tar.departure_epoch(None, NOW), NOW_EPOCH)
        self.assertEqual(tar.departure_epoch("", NOW), NOW_EPOCH)

    def test_the_offset_of_a_valid_time_is_respected(self):
        # 18:00 +07:00 is 11:00Z, after NOW at 10:07Z.
        self.assertEqual(tar.departure_epoch("2026-10-05T18:00:00+07:00", NOW), int(datetime(2026, 10, 5, 11, 0, tzinfo=timezone.utc).timestamp()))

    def test_a_z_suffix_is_read(self):
        self.assertEqual(tar.departure_epoch("2026-10-05T12:00:00Z", NOW), int(datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc).timestamp()))

    def test_a_valid_time_that_is_not_a_time_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            tar.departure_epoch("tomorrow", NOW)
        self.assertIn("valid_time", str(caught.exception))

    def test_the_departure_is_a_whole_number_of_seconds(self):
        self.assertIsInstance(tar.departure_epoch(None, NOW + timedelta(microseconds=900000)), int)


class FlagOffTest(unittest.TestCase):
    def test_the_body_equals_todays_and_there_is_one_call(self):
        body = request()
        post = FakePost(ok())
        calls = []

        outcome = tar.route_request(copy.deepcopy(body), post=post, custom_model=areas(calls), enabled=False, now=NOW)

        self.assertEqual(post.bodies, [today_body(body)])
        self.assertNotIn("td_departure", post.bodies[0])
        self.assertEqual(outcome, tar.Outcome(True, 200, ROUTE))

    def test_a_request_without_a_valid_time_gets_no_areas(self):
        body = request()
        del body["valid_time"]
        post = FakePost(ok())
        calls = []

        tar.route_request(copy.deepcopy(body), post=post, custom_model=areas(calls), enabled=False, now=NOW)

        self.assertEqual(post.bodies, [today_body(body)])
        self.assertEqual(calls, [])

    def test_the_flood_fields_are_removed_and_the_vehicle_type_defaults_to_the_profile(self):
        calls = []
        post = FakePost(ok())

        tar.route_request(request(buffer=30, vehicle_type="truck"), post=post, custom_model=areas(calls), enabled=False, now=NOW)

        self.assertEqual(calls, [("2026-10-05T10:00:00+00:00", "truck", "latest")])
        self.assertNotIn("buffer", post.bodies[0])
        self.assertNotIn("vehicle_type", post.bodies[0])

    def test_a_graphhopper_error_comes_back_as_an_error(self):
        outcome = tar.route_request(request(), post=FakePost(error()), custom_model=areas([]), enabled=False, now=NOW)

        self.assertEqual(outcome, tar.Outcome(False, 400, '{"message": "Connection between locations not found"}'))


class FlagOnTest(unittest.TestCase):
    def test_an_applied_route_is_sent_with_the_departure_and_without_the_areas(self):
        body = request()
        post = FakePost(ok({"td.status": "applied", "td.run": "20261005T000000"}))
        calls = []

        outcome = tar.route_request(copy.deepcopy(body), post=post, custom_model=areas(calls), enabled=True, now=NOW)

        self.assertEqual(len(post.bodies), 1)
        sent = post.bodies[0]
        self.assertEqual(sent["td_departure"], NOW_EPOCH, "valid_time is 10:00 and now is 10:07")
        self.assertNotIn("custom_model", sent)
        self.assertNotIn("ch.disable", sent)
        self.assertEqual(calls, [], "the areas are not read when the engine judges the roads")
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.data["hints"]["td.status"], "applied")

    def test_a_future_valid_time_is_the_departure(self):
        later = NOW + timedelta(hours=1)
        post = FakePost(ok({"td.status": "applied"}))

        tar.route_request(request(valid_time=later.isoformat()), post=post, custom_model=areas([]), enabled=True, now=NOW)

        self.assertEqual(post.bodies[0]["td_departure"], int(later.timestamp()))

    def test_an_unknown_answer_passes_through_with_one_call(self):
        post = FakePost(ok({"td.status": "unknown", "td.run": "20261005T000000"}))

        outcome = tar.route_request(request(), post=post, custom_model=areas([]), enabled=True, now=NOW)

        self.assertEqual(len(post.bodies), 1)
        self.assertEqual(outcome.data["hints"]["td.status"], "unknown")

    def test_a_fallback_sends_todays_request_and_keeps_the_flag_and_the_reason(self):
        body = request()
        post = FakePost(
            ok({"td.status": "fallback", "td.reason": "stale edge depth table: run X was built for graph hash AAA, but the loaded graph has hash BBB"}),
            ok(),
        )
        calls = []

        outcome = tar.route_request(copy.deepcopy(body), post=post, custom_model=areas(calls), enabled=True, now=NOW)

        self.assertEqual(len(post.bodies), 2)
        self.assertEqual(post.bodies[1], today_body(body), "the second request is exactly today's")
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.data["hints"]["td.status"], "fallback")
        self.assertIn("AAA", outcome.data["hints"]["td.reason"])
        self.assertIn("BBB", outcome.data["hints"]["td.reason"])
        self.assertEqual(outcome.data["paths"], ROUTE["paths"])

    def test_a_graphhopper_that_does_not_know_the_hint_is_a_fallback(self):
        post = FakePost(ok(), ok())

        outcome = tar.route_request(request(), post=post, custom_model=areas([]), enabled=True, now=NOW)

        self.assertEqual(len(post.bodies), 2)
        self.assertEqual(outcome.data["hints"]["td.status"], "fallback")
        self.assertIn("did not report", outcome.data["hints"]["td.reason"])

    def test_a_response_with_no_hints_at_all_still_gets_the_flag(self):
        bare = {"ok": True, "status": 200, "json": {"paths": ROUTE["paths"]}}
        post = FakePost(bare, bare)

        outcome = tar.route_request(request(), post=post, custom_model=areas([]), enabled=True, now=NOW)

        self.assertEqual(outcome.data["hints"]["td.status"], "fallback")

    def test_a_fallback_without_a_valid_time_sends_no_areas(self):
        body = request()
        del body["valid_time"]
        post = FakePost(ok({"td.status": "fallback", "td.reason": "no table"}), ok())

        tar.route_request(copy.deepcopy(body), post=post, custom_model=areas([]), enabled=True, now=NOW)

        self.assertEqual(post.bodies[1], today_body(body))
        self.assertEqual(post.bodies[0]["td_departure"], NOW_EPOCH)

    def test_an_error_from_the_first_request_passes_through_and_is_not_retried(self):
        post = FakePost(error())

        outcome = tar.route_request(request(), post=post, custom_model=areas([]), enabled=True, now=NOW)

        self.assertEqual(len(post.bodies), 1)
        self.assertEqual(outcome, tar.Outcome(False, 400, '{"message": "Connection between locations not found"}'))

    def test_an_error_from_the_fallback_request_is_returned(self):
        post = FakePost(ok({"td.status": "fallback", "td.reason": "no table"}), error(503, "down"))

        outcome = tar.route_request(request(), post=post, custom_model=areas([]), enabled=True, now=NOW)

        self.assertEqual(outcome, tar.Outcome(False, 503, "down"))

    def test_an_unparsable_valid_time_is_an_error_not_a_fallback(self):
        with self.assertRaises(ValueError):
            tar.route_request(request(valid_time="soon"), post=FakePost(), custom_model=areas([]), enabled=True, now=NOW)

    def test_the_clients_own_td_fields_are_not_trusted(self):
        # A client must not pick the departure, the margin, or the policy (US-053 says the same for the endpoint).
        post = FakePost(ok({"td.status": "applied"}))

        tar.route_request(request(td_departure=1, td_limit_cm=1), post=post, custom_model=areas([]), enabled=True, now=NOW)

        self.assertEqual(post.bodies[0]["td_departure"], NOW_EPOCH)
        self.assertNotIn("td_limit_cm", post.bodies[0])

    def test_the_clients_td_fields_are_removed_with_the_flag_off_too(self):
        post = FakePost(ok())

        tar.route_request(request(td_departure=1, td_limit_cm=1), post=post, custom_model=areas([]), enabled=False, now=NOW)

        self.assertNotIn("td_departure", post.bodies[0])
        self.assertNotIn("td_limit_cm", post.bodies[0])


class ProfileLimitsTest(unittest.TestCase):
    """td_limit_cm in config.yml must equal threshold_cm in flood_utils.py, or the engine and the map disagree."""

    ROOT = Path(__file__).resolve().parents[1]

    def limits_in_config(self):
        """Reads the profiles block line by line, so the test needs no YAML library."""
        limits, name = {}, None
        for line in (self.ROOT / "graphhopper" / "config.yml").read_text(encoding="utf-8").splitlines():
            named = re.match(r"\s+- name: (\w+)\s*$", line)
            if named:
                name = named.group(1)
            limit = re.match(r"\s+td_limit_cm: (\d+)\s*$", line)
            if limit and name:
                limits[name] = int(limit.group(1))
        return limits

    def test_the_limits_equal_the_thresholds_of_flood_utils(self):
        sys.path.insert(0, str(self.ROOT / "scripts"))
        import flood_utils

        limits = self.limits_in_config()
        self.assertTrue(limits, "no td_limit_cm in config.yml")
        for profile, limit in limits.items():
            self.assertEqual(limit, flood_utils.vehicle_threshold_cm(profile), profile)

    def test_all_four_vehicles_have_a_limit(self):
        self.assertEqual(self.limits_in_config(), {"motorbike": 20, "car": 30, "truck": 35, "foot": 40})


if __name__ == "__main__":
    unittest.main()
