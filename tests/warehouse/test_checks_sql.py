"""Static rules of the SQL checks (they run against BigQuery only from make)."""

import re

import pytest

from warehouse.checks import (
    CHECKS_DIR,
    check_files,
    check_name,
    referenced_parameters,
    references_view,
)
from warehouse.ddl import parse_sql, strip_comments_and_strings
from warehouse.expectations import load_expectations

EXPECTED_FILES = [
    "01_conteo_filas.sql",
    "02_unicidad_claves.sql",
    "03_nulos.sql",
    "04_dominios.sql",
    "05_reconciliacion_join.sql",
    "06_precio_unitario.sql",
    "07_reconciliacion_vista.sql",
]
EXPECTED_PARAMETERS = {
    "conteo_filas": ["filas_clue_cat", "filas_compras", "filas_cuadro_basico"],
    "unicidad_claves": [],
    "nulos": [],
    "dominios": ["fecha_fin", "fecha_inicio"],
    "reconciliacion_join": ["huerfanos_clave", "huerfanos_clue"],
    "precio_unitario": ["dispersion_maxima", "precio_maximo", "precio_minimo"],
    "reconciliacion_vista": [],
}
CONTRACT = ("CHEQUEO", "OBJETO", "DETALLE", "ESPERADO", "OBTENIDO")


def _code(path):
    return strip_comments_and_strings(path.read_text(encoding="utf-8"))


def test_exactly_the_seven_checks():
    assert [p.name for p in check_files()] == EXPECTED_FILES


@pytest.mark.parametrize("path", check_files(), ids=lambda p: p.name)
def test_header_comment(path):
    assert path.read_text(encoding="utf-8").startswith("-- ")


@pytest.mark.parametrize("path", check_files(), ids=lambda p: p.name)
def test_parameters_are_known(path):
    used = referenced_parameters(path.read_text(encoding="utf-8"))
    assert used == EXPECTED_PARAMETERS[check_name(path)]
    assert set(used) <= set(load_expectations())


@pytest.mark.parametrize("path", check_files(), ids=lambda p: p.name)
def test_style_rules(path):
    code = _code(path)
    assert not re.search(r"SELECT\s+\*", code, re.IGNORECASE)
    assert not re.search(r"[\w`-]+\.farma_analytics\.", code)
    assert not re.search(r"\b(LEFT|RIGHT|FULL|CROSS)\s+(OUTER\s+)?JOIN\b", code, re.IGNORECASE)
    assert not re.search(r"\bJOIN\b", re.sub(r"INNER\s+JOIN", "", code, flags=re.IGNORECASE))
    for ref in re.finditer(r"farma_analytics\.\w+(\s+\w+)?", code):
        assert ref.group(1) and ref.group(1).strip().upper() == "AS", ref.group(0)


@pytest.mark.parametrize("path", check_files(), ids=lambda p: p.name)
def test_final_select_follows_the_contract(path):
    sql = "CREATE SCHEMA IF NOT EXISTS x;\n" + path.read_text(encoding="utf-8")
    statement = parse_sql(sql).statements[-1]
    assert statement.kind == "query"
    tail = statement.text
    final_select = tail[tail.rfind("\nSELECT") :] if "\nSELECT" in tail else tail
    names = re.findall(
        r"(?:\bAS\s+|\.)(" + "|".join(CONTRACT) + r")\b,?\s*$", final_select, re.MULTILINE
    )
    assert names[:5] == list(CONTRACT)


def test_view_check_reads_the_view_and_the_three_tables():
    code = _code(CHECKS_DIR / "07_reconciliacion_vista.sql")
    for relation in ("v_compras_farma_completa", "COMPRAS", "CLUE_CAT", "CUADRO_BASICO"):
        assert re.search(rf"farma_analytics\.{relation}\s+AS\s", code), relation
    assert references_view(code)
    assert not any(references_view(_code(p)) for p in check_files() if p.name[:2] != "07")


def test_checks_dir_has_only_negative_subdir():
    assert [p.name for p in CHECKS_DIR.iterdir() if p.is_dir()] == ["negativos"]
