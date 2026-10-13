import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_db_tests  # noqa: E402
from run_db_tests import Counts  # noqa: E402

DATASETS = ("minio_custom_test", "flood_metrics_test")


class ScratchNameTests(unittest.TestCase):
    def test_names_carry_the_token_and_end_in_test(self):
        self.assertEqual(run_db_tests.scratch_names("0a1b2c3d"), ("us128_0a1b2c3d_pg_test", "us128_0a1b2c3d_ts_test"))

    def test_a_scratch_name_passes_the_guard(self):
        run_db_tests.check_scratch_name("us128_0a1b2c3d_pg_test", "minio_custom", DATASETS)

    def test_a_name_without_the_suffix_is_refused(self):
        with self.assertRaisesRegex(ValueError, "does not end in '_test'"):
            run_db_tests.check_scratch_name("minio_custom", "postgres", DATASETS)

    def test_a_dataset_database_is_refused(self):
        with self.assertRaisesRegex(ValueError, "'minio_custom_test' is a dataset database"):
            run_db_tests.check_scratch_name("minio_custom_test", "minio_custom", DATASETS)

    def test_the_admin_database_is_refused(self):
        with self.assertRaisesRegex(ValueError, "is the production database"):
            run_db_tests.check_scratch_name("a_test", "a_test", ())


class BuildDsnTests(unittest.TestCase):
    def test_a_plain_dsn(self):
        self.assertEqual(
            run_db_tests.build_dsn("minio_custom", "secret", "127.0.0.1", 55001, "us128_x_pg_test"),
            "postgresql://minio_custom:secret@127.0.0.1:55001/us128_x_pg_test",
        )

    def test_special_characters_in_the_password_are_escaped(self):
        self.assertEqual(
            run_db_tests.build_dsn("u", "p@ss/w:rd#1", "127.0.0.1", 5, "d"),
            "postgresql://u:p%40ss%2Fw%3Ard%231@127.0.0.1:5/d",
        )


class SummaryTests(unittest.TestCase):
    def test_passed_and_skipped(self):
        self.assertEqual(run_db_tests.parse_summary("..s\n12 passed, 3 skipped in 1.20s\n"), Counts(12, 0, 0, 3))

    def test_all_four_counts_and_warnings(self):
        line = "2 failed, 10 passed, 1 skipped, 3 warnings, 1 error in 5.00s"
        self.assertEqual(run_db_tests.parse_summary(line), Counts(10, 2, 1, 1))

    def test_a_decorated_line_with_a_duration_in_brackets(self):
        self.assertEqual(run_db_tests.parse_summary("== 4 passed in 0.10s (0:00:00) =="), Counts(4, 0, 0, 0))

    def test_plural_errors(self):
        self.assertEqual(run_db_tests.parse_summary("3 errors in 0.50s"), Counts(0, 0, 3, 0))

    def test_no_summary_gives_none(self):
        self.assertIsNone(run_db_tests.parse_summary("Traceback\nValueError"))

    def test_no_tests_ran_is_zero_counts(self):
        self.assertEqual(run_db_tests.summarize(5, "no tests ran in 0.01s\n"), Counts())

    def test_a_crash_without_a_summary_is_one_error(self):
        self.assertEqual(run_db_tests.summarize(2, "Traceback"), Counts(errors=1))

    def test_a_usage_error_exit_with_a_clean_summary_is_one_error(self):
        self.assertEqual(run_db_tests.summarize(4, "3 passed in 0.1s"), Counts(3, 0, 1, 0))

    def test_a_failing_run_keeps_its_counts(self):
        self.assertEqual(run_db_tests.summarize(1, "1 failed, 2 passed in 0.1s"), Counts(2, 1, 0, 0))


class CompareCountsTests(unittest.TestCase):
    BEFORE = {
        "a_test": {"graph_edge": 10, "flood_segment_metrics": None},
        "b_test": {"graph_edge": None, "flood_segment_metrics": 0},
    }

    def test_equal_counts_give_no_difference(self):
        self.assertEqual(run_db_tests.compare_counts(self.BEFORE, self.BEFORE), [])

    def test_a_changed_count_is_named(self):
        after = {"a_test": {"graph_edge": 9, "flood_segment_metrics": None}, "b_test": self.BEFORE["b_test"]}
        self.assertEqual(run_db_tests.compare_counts(self.BEFORE, after), ["a_test.graph_edge: 10 before, 9 after"])

    def test_a_table_that_appeared_is_a_difference(self):
        after = {"a_test": self.BEFORE["a_test"], "b_test": {"graph_edge": 0, "flood_segment_metrics": 0}}
        self.assertEqual(run_db_tests.compare_counts(self.BEFORE, after), ["b_test.graph_edge: None before, 0 after"])


class FormatTests(unittest.TestCase):
    def test_suite_table_with_total(self):
        table = run_db_tests.format_suite_table([("scripts/database", Counts(10, 1, 0, 2)), ("test", Counts(5, 0, 3, 0))])
        self.assertEqual(
            table,
            "\n".join(
                [
                    "folder            passed  failed  errors  skipped",
                    "----------------  ------  ------  ------  -------",
                    "scripts/database      10       1       0        2",
                    "test                   5       0       3        0",
                    "----------------  ------  ------  ------  -------",
                    "total                 15       1       3        2",
                ]
            ),
        )

    def test_dataset_counts_mark_an_absent_table(self):
        counts = {"a_test": {"graph_edge": 7, "flood_extent_step": None}}
        self.assertEqual(
            run_db_tests.format_dataset_counts(counts, counts),
            "\n".join(
                [
                    "table                           before         after",
                    "a_test.graph_edge                    7             7",
                    "a_test.flood_extent_step        absent        absent",
                ]
            ),
        )

    def test_scrub_hides_a_password_and_its_escaped_form(self):
        self.assertEqual(run_db_tests.scrub("x p@ss y p%40ss", ["p@ss"]), "x *** y ***")


class PlanTests(unittest.TestCase):
    def test_tunnel_command(self):
        self.assertEqual(
            run_db_tests.tunnel_command(6001, 6002),
            [
                "ssh", "-N", "-o", "ExitOnForwardFailure=yes", "-o", "BatchMode=yes",
                "-L", "6001:127.0.0.1:5433", "-L", "6002:127.0.0.1:5434", "tecotec@100.67.84.55",
            ],
        )

    def test_the_top_level_scripts_suite_lists_files_only(self):
        paths = run_db_tests.suite_paths("scripts")
        self.assertIn("scripts/test_standing_flood.py", paths)
        self.assertTrue(all(p.count("/") == 1 for p in paths))

    def test_only_selects_one_suite(self):
        self.assertEqual(run_db_tests.selected_suites("test"), ["test"])


if __name__ == "__main__":
    unittest.main()


class ParseWorkerEnvironmentTest(unittest.TestCase):
    ENV = "PATH=/usr/bin\nPOSTGRES_USER=minio_custom\nPOSTGRES_PASSWORD=pw1\nPOSTGRES_DB=minio_custom\nTIMESCALE_PASSWORD=pw2\n"

    def test_unset_timescale_user_and_db_take_the_db_config_defaults(self):
        values = run_db_tests.parse_worker_environment(self.ENV)
        self.assertEqual(values["TIMESCALE_USER"], "flood_metrics")
        self.assertEqual(values["TIMESCALE_DB"], "flood_metrics")
        self.assertEqual(values["POSTGRES_PASSWORD"], "pw1")

    def test_a_set_variable_wins_over_the_default(self):
        values = run_db_tests.parse_worker_environment(self.ENV + "TIMESCALE_USER=other\n")
        self.assertEqual(values["TIMESCALE_USER"], "other")

    def test_a_missing_password_raises(self):
        with self.assertRaisesRegex(RuntimeError, "TIMESCALE_PASSWORD"):
            run_db_tests.parse_worker_environment("POSTGRES_USER=a\nPOSTGRES_PASSWORD=b\nPOSTGRES_DB=c\n")
