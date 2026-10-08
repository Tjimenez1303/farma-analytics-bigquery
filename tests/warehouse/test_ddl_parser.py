"""DDL analysis on a small fixture file."""

import pytest

from warehouse.ddl import DdlError, parse_file, parse_sql, strip_comments_and_strings, unquote

FIXTURE = "tests/fixtures/sql/ddl_minima.sql"


@pytest.fixture
def parsed(repo_root):
    return parse_file(repo_root / FIXTURE)


def test_statements_in_order_without_terminator(parsed):
    kinds = [(s.kind, s.target) for s in parsed.statements]
    assert kinds == [
        ("create_schema", "ejemplo"),
        ("create_table", "ejemplo.UNO"),
        ("create_table", "ejemplo.DOS"),
        ("other", ""),
    ]
    assert parsed.statements[0].text.startswith("CREATE SCHEMA IF NOT EXISTS ejemplo")
    assert all(not s.text.rstrip().endswith(";") for s in parsed.statements)
    assert all("Minimal DDL" not in s.text for s in parsed.statements)


def test_dataset_spec(parsed):
    assert parsed.dataset.name == "ejemplo"
    assert parsed.dataset.location == "US"
    assert parsed.dataset.description == "Dataset de prueba, con coma y acentos: ñandú."
    assert parsed.dataset.labels == {"project": "demo", "env": "test"}


def test_table_specs(parsed):
    uno, dos = parsed.tables
    assert uno.ref == "ejemplo.UNO"
    assert uno.description == "Tabla uno. Grano: una fila por ID."
    assert [(c.name, c.type, c.mode) for c in uno.columns] == [
        ("ID", "STRING", "REQUIRED"),
        ("VALOR", "NUMERIC", "NULLABLE"),
    ]
    assert uno.columns[0].description == "Llave, única."
    assert uno.columns[1].description == "Valor con 'comillas' escapadas."
    assert [(c.name, c.type, c.mode) for c in dos.columns] == [
        ("ID", "STRING", "REQUIRED"),
        ("CANTIDAD", "INT64", "REQUIRED"),
        ("DIA", "DATE", "NULLABLE"),
    ]


def test_invalid_sql_raises():
    with pytest.raises(DdlError, match="bigquery"):
        parse_sql("CREATE TABLE x (a STRING NOT NULL,,);")


def test_missing_schema_raises():
    with pytest.raises(DdlError, match="CREATE SCHEMA"):
        parse_sql("CREATE TABLE IF NOT EXISTS d.T (A STRING);")


def test_unquote_and_strip():
    assert unquote("'a\\'b'") == "a'b"
    assert unquote('"x"') == "x"
    assert "farma" not in strip_comments_and_strings("SELECT 1 -- farma\n/* farma */ 'farma'")
