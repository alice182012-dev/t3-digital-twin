"""Each reader role's grants come from its list on the core output contract page and name only those tables.

    python3 test_create_routing_reader_role.py

Offline. Reads artifacts/docs/concepts/core-output-contract.md, or CORE_CONTRACT_PAGE when set.
"""

from __future__ import annotations

import contextlib
import io
import os

from create_routing_reader_role import grant_statements, page_path, parse_reader_roles, reader_env
from create_routing_reader_role import main as create_role


def _role_tables(role: str) -> frozenset[str]:
    return parse_reader_roles(page_path().read_text(encoding="utf-8"))[role]


def test_routing_reader_grants_name_exactly_its_tables() -> None:
    assert grant_statements("routing_reader", "minio_custom", _role_tables("routing_reader")) == [
        'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "routing_reader"',
        'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM "routing_reader"',
        'REVOKE CREATE ON SCHEMA public FROM "routing_reader"',
        'GRANT CONNECT ON DATABASE "minio_custom" TO "routing_reader"',
        'GRANT USAGE ON SCHEMA public TO "routing_reader"',
        'GRANT SELECT ON public."flood_depth_raster_tile" TO "routing_reader"',
        'GRANT SELECT ON public."flood_extent_polygon" TO "routing_reader"',
        'GRANT SELECT ON public."flood_extent_step" TO "routing_reader"',
        'GRANT SELECT ON public."flood_road_file" TO "routing_reader"',
        'GRANT SELECT ON public."flood_road_values" TO "routing_reader"',
        'GRANT SELECT ON public."flood_run_output" TO "routing_reader"',
        'GRANT SELECT ON public."graph_edge" TO "routing_reader"',
    ]


def test_analysis_reader_grants_name_exactly_its_tables() -> None:
    assert grant_statements("analysis_reader", "minio_custom", _role_tables("analysis_reader")) == [
        'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "analysis_reader"',
        'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM "analysis_reader"',
        'REVOKE CREATE ON SCHEMA public FROM "analysis_reader"',
        'GRANT CONNECT ON DATABASE "minio_custom" TO "analysis_reader"',
        'GRANT USAGE ON SCHEMA public TO "analysis_reader"',
        'GRANT SELECT ON public."flood_depth_raster_tile" TO "analysis_reader"',
        'GRANT SELECT ON public."flood_extent_polygon" TO "analysis_reader"',
        'GRANT SELECT ON public."flood_extent_step" TO "analysis_reader"',
        'GRANT SELECT ON public."flood_road_values" TO "analysis_reader"',
        'GRANT SELECT ON public."flood_run_output" TO "analysis_reader"',
    ]


def test_each_role_reads_its_own_variables() -> None:
    assert reader_env("routing_reader") == ("ROUTING_READER_USER", "ROUTING_READER_PASSWORD")
    assert reader_env("analysis_reader") == ("ANALYSIS_READER_USER", "ANALYSIS_READER_PASSWORD")


def _run_main(argv: list[str]) -> tuple[int, str]:
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code = create_role(argv)
    return code, stderr.getvalue()


def test_an_unknown_or_missing_role_prints_the_choices() -> None:
    usage = "Usage: create_routing_reader_role.py ROLE, where ROLE is one of analysis_reader, routing_reader.\n"
    assert _run_main(["create_routing_reader_role.py"]) == (2, usage)
    assert _run_main(["create_routing_reader_role.py", "road_reader"]) == (2, usage)


def test_a_role_without_its_password_stops_before_connecting() -> None:
    saved = os.environ.pop("ANALYSIS_READER_PASSWORD", None)
    try:
        assert _run_main(["create_routing_reader_role.py", "analysis_reader"]) == (
            1,
            "Set ANALYSIS_READER_PASSWORD to the password analysis_reader will use.\n",
        )
    finally:
        if saved is not None:
            os.environ["ANALYSIS_READER_PASSWORD"] = saved


def test_an_identifier_that_needs_quoting_is_refused() -> None:
    for role, table in (('reader"; DROP ROLE x; --', "graph_edge"), ("routing_reader", "Mixed Case")):
        try:
            grant_statements(role, "minio_custom", frozenset({table}))
        except ValueError:
            continue
        raise AssertionError(f"{role!r} and {table!r} were accepted")


def main() -> int:
    test_routing_reader_grants_name_exactly_its_tables()
    test_analysis_reader_grants_name_exactly_its_tables()
    test_each_role_reads_its_own_variables()
    test_an_unknown_or_missing_role_prints_the_choices()
    test_a_role_without_its_password_stops_before_connecting()
    test_an_identifier_that_needs_quoting_is_refused()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
