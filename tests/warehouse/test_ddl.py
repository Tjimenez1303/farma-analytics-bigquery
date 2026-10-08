"""Rules of contracts/ddl.md on sql/farma_analytics.sql."""

import re

import pytest

from generator.pipeline import HEADERS
from warehouse.ddl import strip_comments_and_strings

# Columns, types and modes from data-model.md.
EXPECTED = {
    "COMPRAS": [
        ("CLUE", "STRING", "REQUIRED"),
        ("CLAVE", "STRING", "REQUIRED"),
        ("COD_PROVEEDOR", "STRING", "REQUIRED"),
        ("MARCA", "STRING", "NULLABLE"),
        ("FABRICANTE", "STRING", "NULLABLE"),
        ("PIEZAS", "INT64", "REQUIRED"),
        ("IMPORTE", "NUMERIC", "REQUIRED"),
        ("FECHA", "DATE", "REQUIRED"),
    ],
    "CLUE_CAT": [
        ("CLUE", "STRING", "REQUIRED"),
        ("ENTIDAD", "STRING", "NULLABLE"),
        ("INSTITUCION", "STRING", "NULLABLE"),
        ("DELEGACION", "STRING", "NULLABLE"),
        ("GRUPO_INSTITUCIONAL", "STRING", "NULLABLE"),
        ("NIVEL_ATENCION", "STRING", "NULLABLE"),
        ("MUNICIPIO", "STRING", "NULLABLE"),
    ],
    "CUADRO_BASICO": [
        ("CLAVE", "STRING", "REQUIRED"),
        ("DESCRIPCION", "STRING", "NULLABLE"),
        ("MOLECULA", "STRING", "NULLABLE"),
        ("GRUPO_TERAPEUTICO", "STRING", "NULLABLE"),
        ("PRESENTACION", "STRING", "NULLABLE"),
        ("FABRICANTE", "STRING", "NULLABLE"),
    ],
}
FORBIDDEN_IN_DDL = (
    "AS SELECT",
    "PARTITION BY",
    "CLUSTER BY",
    "PRIMARY KEY",
    "FOREIGN KEY",
    "EXPIRATION_TIMESTAMP",
    "DEFAULT_TABLE_EXPIRATION_DAYS",
)


def _ddl_statements(ddl):
    return [s for s in ddl.statements if s.kind in ("create_schema", "create_table")]


def test_schema_then_three_tables_first(ddl):
    first = [(s.kind, s.target) for s in ddl.statements[:4]]
    assert first == [
        ("create_schema", "farma_analytics"),
        ("create_table", "farma_analytics.COMPRAS"),
        ("create_table", "farma_analytics.CLUE_CAT"),
        ("create_table", "farma_analytics.CUADRO_BASICO"),
    ]
    assert len(_ddl_statements(ddl)) == 4


def test_ddl_statements_use_if_not_exists(ddl):
    for statement in _ddl_statements(ddl):
        assert " IF NOT EXISTS " in statement.text.upper().replace("\n", " "), statement.target


@pytest.mark.parametrize("token", FORBIDDEN_IN_DDL)
def test_forbidden_constructs_in_ddl_statements(ddl, token):
    for statement in _ddl_statements(ddl):
        code = " ".join(strip_comments_and_strings(statement.text).upper().split())
        assert token not in code, statement.target


def test_whole_file_has_no_replace_table_nor_project_id(repo_root):
    code = strip_comments_and_strings(
        (repo_root / "sql" / "farma_analytics.sql").read_text(encoding="utf-8")
    )
    assert not re.search(r"OR\s+REPLACE\s+TABLE", code, re.IGNORECASE)
    assert not re.search(r"[\w`-]+\.farma_analytics\.", code)


def test_location_matches_bigqueryrc(ddl, repo_root):
    rc = (repo_root / ".bigqueryrc").read_text(encoding="utf-8")
    location = re.search(r"^--location=(\S+)$", rc, re.MULTILINE).group(1)
    assert ddl.dataset.location.upper() == location.upper()


def test_labels_match_makefile(ddl, repo_root):
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    line = re.search(r"^BQ_LABELS := (.+)$", makefile, re.MULTILINE).group(1)
    job_labels = dict(item.split("=", 1)[1].split(":", 1) for item in line.split())
    labels = ddl.dataset.labels
    assert {k: labels[k] for k in ("project", "env")} == job_labels
    assert labels.get("owner")
    for key, value in labels.items():
        assert key == key.lower() and value == value.lower()


def test_columns_types_and_modes(ddl):
    tables = {t.name: [(c.name, c.type, c.mode) for c in t.columns] for t in ddl.tables}
    assert tables == EXPECTED


def test_column_order_matches_csv_headers(ddl):
    for table in ddl.tables:
        assert [c.name for c in table.columns] == HEADERS[table.name]


def test_descriptions_everywhere(ddl):
    texts = [ddl.dataset.description]
    for table in ddl.tables:
        texts.append(table.description)
        texts.extend(c.description for c in table.columns)
    for text in texts:
        assert text.strip()
        assert "'" not in text and ";" not in text


def test_table_descriptions_declare_grain(ddl):
    for table in ddl.tables:
        assert "Grano:" in table.description, table.name
