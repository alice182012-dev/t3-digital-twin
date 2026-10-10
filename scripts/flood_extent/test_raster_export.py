"""Run it as a file with the flood_extent folder on the path: PYTHONPATH=scripts/flood_extent python3 -I ..."""
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import raster_export


def fake_connection(valid_times, raster_by_time):
    """A connection whose cursor answers the two queries of export_run."""
    cur = MagicMock()
    state = {}

    def execute(sql, params=None):
        state["params"] = params
        state["sql"] = sql

    def fetchall():
        return [(value,) for value in valid_times]

    def fetchone():
        return (raster_by_time[state["params"]["valid_time_utc"]],)

    cur.execute.side_effect = execute
    cur.fetchall.side_effect = fetchall
    cur.fetchone.side_effect = fetchone
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


class DepthFilenameTests(unittest.TestCase):
    def test_a_utc_instant_is_named_in_vietnam_local_time(self):
        self.assertEqual(raster_export.depth_filename(datetime(2026, 9, 24, 10, 6, 39)), "depth_20260924_170639.tif")

    def test_a_step_before_midnight_utc_rolls_the_local_date_forward(self):
        self.assertEqual(raster_export.depth_filename(datetime(2026, 9, 24, 18, 0, 0)), "depth_20260925_010000.tif")


class ExportRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_each_step_is_written_under_its_local_time_name(self):
        first, second = datetime(2026, 9, 24, 10, 6, 39), datetime(2026, 9, 24, 10, 21, 39)
        conn, cur = fake_connection([first, second], {first: b"one", second: b"two"})

        written = raster_export.export_run(conn, "20260924T170639", self.tmp.name, 2)

        names = [path.name for path in written]
        self.assertEqual(names, ["depth_20260924_170639.tif", "depth_20260924_172139.tif"])
        self.assertEqual([Path(path).read_bytes() for path in written], [b"one", b"two"])

    def test_the_step_limit_goes_to_the_query(self):
        first = datetime(2026, 9, 24, 10, 6, 39)
        conn, cur = fake_connection([first], {first: b"one"})

        raster_export.export_run(conn, "20260924T170639", self.tmp.name, 3)

        steps_call = [call for call in cur.execute.call_args_list if call.args[1:] and "steps" in call.args[1]][0]
        self.assertEqual(steps_call.args[1], {"run_ts": "20260924T170639", "steps": 3})

    def test_a_run_without_rows_fails_loudly(self):
        conn, cur = fake_connection([], {})

        with self.assertRaises(ValueError):
            raster_export.export_run(conn, "20260924T170639", self.tmp.name, 2)


if __name__ == "__main__":
    unittest.main()
