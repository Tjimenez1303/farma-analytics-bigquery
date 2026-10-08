"""Negative cases: each check runs on inline rows with a planted error."""

import json

import pytest

from warehouse import commands
from warehouse.checks import (
    NEGATIVE_DIR,
    check_files,
    check_name,
    inline_tables,
    load_negative_case,
)


def _case(path):
    return load_negative_case(NEGATIVE_DIR / f"{path.stem}.json")


def test_one_case_per_check():
    assert sorted(p.stem for p in NEGATIVE_DIR.glob("*.json")) == [p.stem for p in check_files()]


@pytest.mark.parametrize("path", check_files(), ids=lambda p: p.name)
def test_case_rows_have_every_column(path, ddl):
    case = _case(path)
    assert case["esperado"]["CHEQUEO"] == check_name(path)
    assert case["esperado"]["OBJETO"]
    assert sorted(case["tablas"]) == sorted(t.name for t in ddl.tables)
    for table in ddl.tables:
        for row in case["tablas"][table.name]:
            assert list(row) == [c.name for c in table.columns], (path.name, table.name)
            assert all(v is None or isinstance(v, str) for v in row.values())


@pytest.mark.parametrize("path", check_files(), ids=lambda p: p.name)
def test_inline_replaces_every_table(path, ddl):
    sql = inline_tables(path.read_text(encoding="utf-8"), _case(path), ddl.tables)
    assert "farma_analytics." not in sql
    assert "FROM UNNEST(ARRAY<STRUCT<" in sql


def test_inline_select_is_typed_and_escaped(ddl):
    sql = "SELECT compras.CLUE FROM farma_analytics.COMPRAS AS compras"
    row = {
        "CLUE": "A'B",
        "CLAVE": None,
        "COD_PROVEEDOR": "P",
        "MARCA": "M",
        "FABRICANTE": "F",
        "PIEZAS": "3",
        "IMPORTE": "5341.60",
        "FECHA": "2024-01-02",
    }
    case = {"tablas": {"COMPRAS": [row], "CLUE_CAT": [], "CUADRO_BASICO": []}}
    inlined = inline_tables(sql, case, ddl.tables)
    assert "STRUCT<CLUE STRING, CLAVE STRING, COD_PROVEEDOR STRING" in inlined
    assert "PIEZAS INT64, IMPORTE NUMERIC, FECHA DATE>>" in inlined
    assert "CAST('A\\'B' AS STRING)" in inlined
    assert "CAST(NULL AS STRING)" in inlined
    assert "CAST('5341.60' AS NUMERIC)" in inlined
    assert "CAST('2024-01-02' AS DATE)" in inlined
    assert inlined.endswith(") AS compras")


def test_empty_table_is_a_typed_empty_array(ddl):
    sql = "SELECT 1 FROM farma_analytics.CLUE_CAT AS clue_cat"
    case = {"tablas": {"COMPRAS": [], "CLUE_CAT": [], "CUADRO_BASICO": []}}
    assert ">>[]))" in inline_tables(sql, case, ddl.tables)


def _expected_row(path):
    return dict(_case(path)["esperado"], DETALLE="d", ESPERADO="e", OBTENIDO="o")


def test_all_cases_detected(warehouse_env, fake_bq, capsys):
    for path in check_files():
        fake_bq.when(
            fake_bq.query_run(f"'{check_name(path)}' AS CHEQUEO"),
            stdout=json.dumps([_expected_row(path)]),
        )
    assert commands.run_negative_checks_command() == 0
    queries = [c for c in fake_bq.calls if "query" in c.argv]
    assert len(queries) == 2 * len(check_files())
    assert all("farma_analytics." not in c.stdin for c in queries)
    assert not fake_bq.with_verb("show")
    runs = [c for c in queries if "--dry_run" not in c.argv]
    assert all(any(a.startswith("--label=") for a in c.argv) for c in runs)
    assert "Casos negativos: 6 de 6 detectados." in capsys.readouterr().out


def test_undetected_case_fails(warehouse_env, fake_bq, capsys):
    for path in check_files():
        if check_name(path) != "precio_unitario":
            fake_bq.when(
                fake_bq.query_run(f"'{check_name(path)}' AS CHEQUEO"),
                stdout=json.dumps([_expected_row(path)]),
            )
    assert commands.run_negative_checks_command() == 1
    out = capsys.readouterr().out
    assert "FALLO precio_unitario: NO detectó el error" in out
    assert "Casos negativos: 5 de 6 detectados." in out


def test_wrong_object_is_not_detection(warehouse_env, fake_bq, capsys):
    for path in check_files():
        row = _expected_row(path)
        if check_name(path) == "nulos":
            row["OBJETO"] = "COMPRAS.FECHA"
        fake_bq.when(
            fake_bq.query_run(f"'{check_name(path)}' AS CHEQUEO"), stdout=json.dumps([row])
        )
    assert commands.run_negative_checks_command() == 1
    assert "FALLO nulos" in capsys.readouterr().out
