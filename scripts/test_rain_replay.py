import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import rain_replay

EVENT_FILE = Path(__file__).resolve().parent / "rain_events" / "hanoi_20251005_48h.csv"
T0 = datetime(2025, 10, 5, 22, 30, tzinfo=timezone.utc)

SOURCE_ROWS = [
    ("2025-10-05T22:00:00+00:00", 0.0),
    ("2025-10-05T22:30:00+00:00", 1.0),
    ("2025-10-05T23:00:00+00:00", 2.0),
    ("2025-10-05T23:30:00+00:00", 4.0),
    ("2025-10-06T00:00:00+00:00", 0.5),
]


def starts(intervals):
    return [i["startTime"] for i in intervals]


def rates(intervals):
    return [i["values"]["precipitationIntensity"] for i in intervals]


class CutWindowTests(unittest.TestCase):
    def test_cut_keeps_rows_in_the_window_and_rebases_offsets(self):
        cut = rain_replay.cut_window(SOURCE_ROWS, "2025-10-05T22:30:00+00:00", hours=1)
        self.assertEqual(cut, [(0, 1.0), (30, 2.0), (60, 4.0)])

    def test_cut_rejects_a_window_that_runs_past_the_source(self):
        with self.assertRaises(ValueError):
            rain_replay.cut_window(SOURCE_ROWS, "2025-10-05T23:00:00+00:00", hours=2)

    def test_cut_rejects_a_start_that_is_not_a_source_row(self):
        with self.assertRaises(ValueError):
            rain_replay.cut_window(SOURCE_ROWS, "2025-10-05T22:45:00+00:00", hours=1)

    def test_written_event_loads_back_unchanged(self):
        event = [(0, 1.0), (30, 2.0), (60, 4.0)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "event.csv"
            rain_replay.write_event(path, event)
            self.assertEqual(path.read_text().splitlines()[0], "offset_minutes,precipitation_mm_hr")
            self.assertEqual(rain_replay.load_event(path), event)


class ReplayIntervalsTests(unittest.TestCase):
    EVENT = [(0, 1.0), (30, 2.0), (60, 0.0)]

    def test_each_half_hour_rate_holds_for_both_fifteen_minute_intervals(self):
        intervals = rain_replay.replay_intervals(self.EVENT, T0, T0, duration_hours=1, timestep_minutes=15)
        self.assertEqual(rates(intervals), [1.0, 1.0, 2.0, 2.0, 0.0])
        self.assertEqual(
            starts(intervals),
            [
                "2025-10-05T22:30:00Z",
                "2025-10-05T22:45:00Z",
                "2025-10-05T23:00:00Z",
                "2025-10-05T23:15:00Z",
                "2025-10-05T23:30:00Z",
            ],
        )

    def test_a_later_run_reads_its_lookahead_from_its_own_slot(self):
        later = datetime(2025, 10, 5, 23, 0, tzinfo=timezone.utc)
        intervals = rain_replay.replay_intervals(self.EVENT, T0, later, duration_hours=0.5, timestep_minutes=15)
        self.assertEqual(rates(intervals), [2.0, 2.0, 0.0])

    def test_before_the_event_and_after_its_last_sample_the_rate_is_zero(self):
        early = datetime(2025, 10, 5, 22, 0, tzinfo=timezone.utc)
        before = rain_replay.replay_intervals(self.EVENT, T0, early, duration_hours=1, timestep_minutes=15)
        self.assertEqual(rates(before), [0.0, 0.0, 1.0, 1.0, 2.0])
        late = datetime(2025, 10, 5, 23, 15, tzinfo=timezone.utc)
        after = rain_replay.replay_intervals(self.EVENT, T0, late, duration_hours=0.5, timestep_minutes=15)
        self.assertEqual(rates(after), [2.0, 0.0, 0.0])


class EventFileTests(unittest.TestCase):
    def test_committed_event_is_the_48_hour_window_of_the_hyetograph(self):
        event = rain_replay.load_event(EVENT_FILE)
        self.assertEqual(len(event), 97)
        self.assertEqual((event[0][0], event[-1][0]), (0, 2880))
        self.assertEqual(max(rate for _, rate in event), 56.481693)
        total_mm = sum(rate for _, rate in event) * 0.5
        self.assertAlmostEqual(total_mm, 246.8, delta=0.1)

    def test_run_at_the_peak_slot_sees_the_peak_inside_its_two_hour_lookahead(self):
        event = rain_replay.load_event(EVENT_FILE)
        slot = datetime(2025, 10, 6, 21, 0, tzinfo=timezone.utc)
        intervals = rain_replay.replay_intervals(event, T0, slot, duration_hours=2, timestep_minutes=15)
        self.assertEqual(max(rates(intervals)), 56.481693)



# Samples every 30 minutes. Rain of 6 mm/h from minute 30 to 59 and from minute 180 to 209.
TWO_BURSTS = [(0, 0.0), (30, 6.0), (60, 0.0), (90, 0.0), (120, 0.0), (150, 0.0), (180, 6.0), (210, 0.0)]


def plan(threshold, event=TWO_BURSTS, hours=3):
    return rain_replay.simulating_slots(event, T0, threshold, hours, lookahead_hours=0.5, timestep_minutes=15)


class SimulatingSlotsTests(unittest.TestCase):
    def test_a_slot_simulates_when_any_rate_in_its_lookahead_reaches_the_threshold(self):
        slots = plan(5.0)
        self.assertEqual([s.simulates for s in slots], [True] * 4 + [False] * 6 + [True] * 2)
        self.assertEqual([s.offset_minutes for s in slots], list(range(0, 180, 15)))

    def test_a_rate_equal_to_the_threshold_counts_like_the_gate_does(self):
        self.assertEqual(sum(s.simulates for s in plan(6.0)), 6)
        self.assertEqual(sum(s.simulates for s in plan(6.01)), 0)

    def test_a_chain_starts_at_the_first_run_and_after_each_dry_gap(self):
        starts = [s.offset_minutes for s in plan(5.0) if s.starts_chain]
        self.assertEqual(starts, [0, 150])

    def test_chain_lengths_list_each_run_of_consecutive_simulating_slots(self):
        self.assertEqual(rain_replay.chain_lengths(plan(5.0)), [4, 2])

    def test_a_run_hotstarts_after_a_gap_of_up_to_four_slots_and_cold_starts_after_a_longer_one(self):
        def cold(flags):
            return [s.cold_start for s in rain_replay.plan_slots(flags, timestep_minutes=15)]

        self.assertEqual(cold([True, False, False, False, True]), [True, False, False, False, False])
        self.assertEqual(cold([True, False, False, False, False, True]), [True, False, False, False, False, True])
        self.assertEqual(cold([True, True, True]), [True, False, False])

    def test_describe_names_each_chain_in_local_time_with_its_run_count_and_start_kind(self):
        lines = rain_replay.describe(plan(5.0), T0, 5.0)
        self.assertEqual(
            lines,
            [
                "gate 5 mm/h: 6 of 12 runs simulate, 2 chains",
                "chain 1: 2025-10-06 05:30 to 2025-10-06 06:15 +07, 4 runs, cold start",
                "chain 2: 2025-10-06 08:00 to 2025-10-06 08:15 +07, 2 runs, cold start",
            ],
        )

    def test_the_committed_event_gives_the_counts_of_the_pipelines_own_gate(self):
        event = rain_replay.load_event(EVENT_FILE)
        expected = {5.0: (104, [26, 46, 10, 10, 12]), 2.0: (156, [36, 120]), 1.0: (174, [52, 122]), 0.01: (192, [192])}
        for threshold, (runs, chains) in expected.items():
            with self.subTest(threshold=threshold):
                slots = rain_replay.simulating_slots(event, T0, threshold, 48, lookahead_hours=2, timestep_minutes=15)
                self.assertEqual(len(slots), 192)
                self.assertEqual(sum(s.simulates for s in slots), runs)
                self.assertEqual(rain_replay.chain_lengths(slots), chains)


def run_cli(*argv, env=None):
    """Run `main` with these arguments. Return its stdout lines and its exit message, or None when it did not exit."""
    out = io.StringIO()
    exit_message = None
    with mock.patch.dict(os.environ, env or {}, clear=env is not None), contextlib.redirect_stdout(out):
        try:
            rain_replay.main(list(argv))
        except SystemExit as stop:
            exit_message = stop.code
    return out.getvalue().splitlines(), exit_message


REPLAY_ENV = {
    "FLOOD_TEST_RAIN_CSV": str(EVENT_FILE),
    "FLOOD_TEST_RAIN_START": "2025-10-05T22:30:00Z",
    "FLOOD_TEST_RAIN_MM_HR": "",
    "FLOOD_RAIN_THRESHOLD_MM_HR": "5",
}
MIXED_RAIN = (
    "Set FLOOD_TEST_RAIN_CSV together with FLOOD_TEST_RAIN_START and without FLOOD_TEST_RAIN_MM_HR, or set none of them"
)


class NextSlotTests(unittest.TestCase):
    def test_the_slot_is_the_first_quarter_hour_at_least_the_lead_ahead(self):
        self.assertEqual(run_cli("next-slot", "2026-10-07T08:12:00Z", "30"), (["2026-10-07T08:45:00Z"], None))

    def test_a_lead_that_lands_on_a_slot_keeps_that_slot(self):
        self.assertEqual(run_cli("next-slot", "2026-10-07T08:00:00Z", "30"), (["2026-10-07T08:30:00Z"], None))

    def test_one_second_past_a_slot_moves_to_the_next_one(self):
        self.assertEqual(run_cli("next-slot", "2026-10-07T08:15:01Z", "0"), (["2026-10-07T08:30:00Z"], None))

    def test_a_local_time_is_read_in_its_own_zone_and_printed_in_utc(self):
        self.assertEqual(run_cli("next-slot", "2026-10-07T15:12:00+07:00", "30"), (["2026-10-07T08:45:00Z"], None))


class CheckTests(unittest.TestCase):
    def test_a_good_setting_prints_the_event_the_runs_the_chains_and_the_unpause_time(self):
        lines, exit_message = run_cli("check", str(EVENT_FILE), "2025-10-05T22:30:00Z", "5")
        self.assertIsNone(exit_message)
        self.assertEqual(
            lines,
            [
                f"event {EVENT_FILE}: 97 rows, 246.8 mm, peak 56.5 mm/h",
                "gate 5 mm/h: 104 of 192 runs simulate, 5 chains",
                "chain 1: 2025-10-06 09:30 to 2025-10-06 15:45 +07, 26 runs, cold start",
                "chain 2: 2025-10-07 00:30 to 2025-10-07 11:45 +07, 46 runs, cold start",
                "chain 3: 2025-10-07 12:30 to 2025-10-07 14:45 +07, 10 runs, hotstart",
                "chain 4: 2025-10-07 17:00 to 2025-10-07 19:15 +07, 10 runs, cold start",
                "chain 5: 2025-10-08 00:00 to 2025-10-08 02:45 +07, 12 runs, cold start",
                "unpause flood_mapping_full before 2025-10-06 05:30 +07 (2025-10-05T22:30:00Z)",
            ],
        )

    def test_a_missing_event_file_stops_with_a_reason_and_prints_nothing(self):
        lines, exit_message = run_cli("check", "/no/such/event.csv", "2025-10-05T22:30:00Z", "5")
        self.assertEqual(lines, [])
        self.assertTrue(exit_message.startswith("/no/such/event.csv does not load: "), exit_message)

    def test_an_event_without_the_header_stops_with_a_reason(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "event.csv"
            path.write_text("minutes,rate\n0,1.0\n30,2.0\n")
            self.assertEqual(
                run_cli("check", str(path), "2025-10-05T22:30:00Z", "5"),
                ([], f"{path} does not load: {path} does not have the header offset_minutes,precipitation_mm_hr"),
            )

    def test_an_empty_event_file_stops_with_a_reason(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "event.csv"
            path.write_text("")
            self.assertEqual(run_cli("check", str(path), "2025-10-05T22:30:00Z", "5"), ([], f"{path} does not load: it is empty"))

    def test_a_start_off_the_fifteen_minute_grid_stops_with_a_reason(self):
        self.assertEqual(
            run_cli("check", str(EVENT_FILE), "2025-10-05T22:40:00Z", "5"),
            ([], "the start 2025-10-05T22:40:00Z is not on a 15-minute slot"),
        )

    def test_a_start_that_is_not_a_time_stops_with_a_reason(self):
        self.assertEqual(run_cli("check", str(EVENT_FILE), "", "5"), ([], "the start '' is not a time"))

    def test_a_gate_no_run_reaches_stops_with_a_reason(self):
        self.assertEqual(
            run_cli("check", str(EVENT_FILE), "2025-10-05T22:30:00Z", "100"),
            ([], "gate 100 mm/h: no run of the event simulates"),
        )


class StatusTests(unittest.TestCase):
    NOW = datetime(2025, 10, 6, 3, 7, tzinfo=timezone.utc)

    def status(self, env):
        mode, detail = rain_replay.read_rain_env(env)
        return rain_replay.status_lines(mode, detail, self.NOW)

    def test_no_test_rain_is_live(self):
        self.assertEqual(self.status({}), ["mode live"])
        self.assertEqual(self.status({"FLOOD_TEST_RAIN_CSV": " ", "FLOOD_RAIN_THRESHOLD_MM_HR": "0.01"}), ["mode live"])

    def test_a_fixed_rate_names_the_rate(self):
        self.assertEqual(self.status({"FLOOD_TEST_RAIN_MM_HR": "30"}), ["mode fixed-rate", "rate 30 mm/h"])

    def test_a_replay_names_the_start_the_runs_and_the_rate_at_the_current_slot(self):
        self.assertEqual(
            self.status(REPLAY_ENV),
            [
                "mode replay",
                f"event {EVENT_FILE}: 97 rows, 246.8 mm, peak 56.5 mm/h",
                "start 2025-10-05T22:30:00Z (2025-10-06 05:30 +07)",
                "gate 5 mm/h: 104 of 192 runs simulate, first 2025-10-06 09:30 +07, last 2025-10-08 02:45 +07",
                "slot 2025-10-06T03:00:00Z rate 1.76775 mm/h, next slot 2025-10-06T03:15:00Z",
            ],
        )

    def test_a_blank_gate_is_the_compose_default_of_5(self):
        lines = self.status({**REPLAY_ENV, "FLOOD_RAIN_THRESHOLD_MM_HR": ""})
        self.assertEqual(lines[3], "gate 5 mm/h: 104 of 192 runs simulate, first 2025-10-06 09:30 +07, last 2025-10-08 02:45 +07")

    def test_a_half_set_or_mixed_combination_is_rejected_like_the_pipeline_does(self):
        for env in (
            {"FLOOD_TEST_RAIN_CSV": str(EVENT_FILE)},
            {"FLOOD_TEST_RAIN_START": "2025-10-05T22:30:00Z"},
            {**REPLAY_ENV, "FLOOD_TEST_RAIN_MM_HR": "30"},
        ):
            with self.subTest(env=env), self.assertRaises(ValueError) as raised:
                rain_replay.read_rain_env(env)
            self.assertEqual(str(raised.exception), MIXED_RAIN)

    def test_the_cli_exits_with_the_reason_for_a_half_set_combination(self):
        self.assertEqual(run_cli("status", env={"FLOOD_TEST_RAIN_START": "2025-10-05T22:30:00Z"}), ([], MIXED_RAIN))

    def test_the_cli_prints_the_status_then_fails_when_the_mode_is_not_the_expected_one(self):
        lines, exit_message = run_cli("status", "--expect-mode", "live", env=REPLAY_ENV)
        self.assertEqual(lines[0], "mode replay")
        self.assertEqual(exit_message, "mode is replay, expected live")

    def test_the_cli_fails_when_the_start_is_not_the_expected_one(self):
        _, exit_message = run_cli(
            "status", "--expect-mode", "replay", "--expect-start", "2025-10-05T22:45:00Z", env=REPLAY_ENV
        )
        self.assertEqual(exit_message, "start is 2025-10-05T22:30:00Z, expected 2025-10-05T22:45:00Z")

    def test_the_cli_passes_when_mode_and_start_match(self):
        lines, exit_message = run_cli(
            "status", "--expect-mode", "replay", "--expect-start", "2025-10-05T22:30:00Z", env=REPLAY_ENV
        )
        self.assertEqual((lines[0], exit_message), ("mode replay", None))

    def test_live_passes_an_expected_live_mode(self):
        self.assertEqual(run_cli("status", "--expect-mode", "live", env={}), (["mode live"], None))


if __name__ == "__main__":
    unittest.main()
