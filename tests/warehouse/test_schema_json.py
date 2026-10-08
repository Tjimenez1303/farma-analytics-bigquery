"""Load schema derived from the DDL."""

import json

from warehouse.ddl import load_schema, write_load_schemas


def test_load_schema_matches_ddl(ddl):
    for table in ddl.tables:
        schema = load_schema(table)
        assert [list(f) for f in schema] == [["name", "type", "mode", "description"]] * len(schema)
        assert [(f["name"], f["type"], f["mode"], f["description"]) for f in schema] == [
            (c.name, c.type, c.mode, c.description) for c in table.columns
        ]
        assert {f["type"] for f in schema} <= {"STRING", "INT64", "NUMERIC", "DATE"}
        assert {f["mode"] for f in schema} <= {"REQUIRED", "NULLABLE"}


def test_write_load_schemas_round_trip(ddl, tmp_path):
    paths = write_load_schemas(ddl.tables, tmp_path)
    assert sorted(paths) == ["CLUE_CAT", "COMPRAS", "CUADRO_BASICO"]
    for table in ddl.tables:
        text = paths[table.name].read_text(encoding="utf-8")
        assert "médica" in text or table.name != "CLUE_CAT"
        assert json.loads(text) == load_schema(table)
