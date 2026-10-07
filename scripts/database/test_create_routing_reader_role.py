"""The reader role's grants come from the core output contract page and name only its tables.

    python3 test_create_routing_reader_role.py

Offline. Reads artifacts/docs/concepts/core-output-contract.md, or CORE_CONTRACT_PAGE when set.
"""

from __future__ import annotations

from create_routing_reader_role import contract_tables, grant_statements, page_path


def test_grants_name_exactly_the_contract_tables() -> None:
    tables = contract_tables(page_path().read_text(encoding="utf-8"))
    assert grant_statements("routing_reader", "minio_custom", tables) == [
        'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "routing_reader"',
        'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM "routing_reader"',
        'REVOKE CREATE ON SCHEMA public FROM "routing_reader"',
        'GRANT CONNECT ON DATABASE "minio_custom" TO "routing_reader"',
        'GRANT USAGE ON SCHEMA public TO "routing_reader"',
        'GRANT SELECT ON public."flood_depth_raster_tile" TO "routing_reader"',
        'GRANT SELECT ON public."flood_extent_polygon" TO "routing_reader"',
        'GRANT SELECT ON public."flood_extent_step" TO "routing_reader"',
        'GRANT SELECT ON public."flood_road_values" TO "routing_reader"',
        'GRANT SELECT ON public."graph_edge" TO "routing_reader"',
    ]


def test_an_identifier_that_needs_quoting_is_refused() -> None:
    for role, table in (('reader"; DROP ROLE x; --', "graph_edge"), ("routing_reader", "Mixed Case")):
        try:
            grant_statements(role, "minio_custom", frozenset({table}))
        except ValueError:
            continue
        raise AssertionError(f"{role!r} and {table!r} were accepted")


def main() -> int:
    test_grants_name_exactly_the_contract_tables()
    test_an_identifier_that_needs_quoting_is_refused()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
