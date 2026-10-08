"""ViewSpec analysis on the fixture and on small inline views."""

import pytest

from warehouse.ddl import DERIVED_TYPES, DdlError, parse_file, parse_sql

FIXTURE = "tests/fixtures/sql/ddl_minima.sql"

BASE = """
CREATE SCHEMA IF NOT EXISTS ejemplo OPTIONS (location = 'US');
CREATE TABLE IF NOT EXISTS ejemplo.UNO (ID STRING NOT NULL, VALOR NUMERIC);
CREATE TABLE IF NOT EXISTS ejemplo.DOS (ID STRING NOT NULL, DIA DATE);
"""


@pytest.fixture
def view(repo_root):
    return parse_file(repo_root / FIXTURE).view


def test_view_spec(view):
    assert view.dataset == "ejemplo"
    assert view.name == "v_ejemplo"
    assert view.ref == "ejemplo.v_ejemplo"
    assert view.description == "Vista de prueba."
    assert view.query.lstrip().startswith("SELECT")


def test_columns_names_descriptions_and_types(view):
    assert [(c.name, c.type, c.mode, c.description) for c in view.columns] == [
        ("ID", "STRING", "NULLABLE", "Llave de UNO."),
        ("CANTIDAD", "INT64", "NULLABLE", "Cantidad de DOS."),
        ("ANIO", "INT64", "NULLABLE", "Año de DIA."),
    ]


def test_derived_types_cover_the_view_columns():
    assert DERIVED_TYPES == {"ANIO": "INT64", "MES": "DATE", "ENTIDAD_ISO": "STRING"}


def _view(columns: str, select: str) -> str:
    return (
        BASE
        + f"CREATE OR REPLACE VIEW ejemplo.v ({columns}) AS SELECT {select} "
        + "FROM ejemplo.UNO AS uno INNER JOIN ejemplo.DOS AS dos ON uno.ID = dos.ID;"
    )


def test_different_column_count_raises():
    with pytest.raises(DdlError, match="columnas"):
        parse_sql(_view("ID, VALOR", "uno.ID"))


def test_output_name_must_match_list_position():
    with pytest.raises(DdlError, match="posición 2"):
        parse_sql(_view("ID, DIA", "uno.ID, uno.VALOR"))
    with pytest.raises(DdlError, match="posición 1"):
        parse_sql(_view("CLAVE", "uno.ID AS LLAVE"))


def test_derived_column_without_type_raises():
    with pytest.raises(DdlError, match="DERIVED_TYPES"):
        parse_sql(_view("ID, DOBLE", "uno.ID, 2 * uno.VALOR AS DOBLE"))


def test_renamed_column_keeps_the_source_type():
    view = parse_sql(_view("ID, FECHA_DOS", "uno.ID, dos.DIA AS FECHA_DOS")).view
    assert [(c.name, c.type) for c in view.columns] == [("ID", "STRING"), ("FECHA_DOS", "DATE")]


def test_description_may_be_a_concat_of_literals_only():
    sql = _view("ID", "uno.ID").replace(
        "CREATE OR REPLACE VIEW ejemplo.v (ID)",
        "CREATE OR REPLACE VIEW ejemplo.v (ID) OPTIONS (description = CONCAT('a, ', 'b'))",
    )
    assert parse_sql(sql).view.description == "a, b"
    with pytest.raises(DdlError, match="CONCAT"):
        parse_sql(sql.replace("CONCAT('a, ', 'b')", "CONCAT('a', CURRENT_DATE())"))


def test_sql_without_view():
    assert parse_sql(BASE).view is None
