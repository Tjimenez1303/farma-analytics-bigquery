"""Rules of contracts/vista.md on section 3 of sql/farma_analytics.sql (rule 11 is make lint)."""

import csv
import re

import pytest

from warehouse.ddl import strip_comments_and_strings

VIEW_REF = "farma_analytics.v_compras_farma_completa"

# Columns and types from data-model.md, in order.
EXPECTED = [
    ("CLUE", "STRING"),
    ("CLAVE", "STRING"),
    ("COD_PROVEEDOR", "STRING"),
    ("MARCA", "STRING"),
    ("FABRICANTE_COMPRA", "STRING"),
    ("PIEZAS", "INT64"),
    ("IMPORTE", "NUMERIC"),
    ("FECHA", "DATE"),
    ("ENTIDAD", "STRING"),
    ("INSTITUCION", "STRING"),
    ("DELEGACION", "STRING"),
    ("GRUPO_INSTITUCIONAL", "STRING"),
    ("NIVEL_ATENCION", "STRING"),
    ("MUNICIPIO", "STRING"),
    ("DESCRIPCION", "STRING"),
    ("MOLECULA", "STRING"),
    ("GRUPO_TERAPEUTICO", "STRING"),
    ("PRESENTACION", "STRING"),
    ("FABRICANTE_CATALOGO", "STRING"),
    ("ANIO", "INT64"),
    ("MES", "DATE"),
    ("ENTIDAD_ISO", "STRING"),
]

# Official ISO 3166-2:MX codes of the 32 federal entities.
ISO_3166_2_MX = {
    "Aguascalientes": "MX-AGU",
    "Baja California": "MX-BCN",
    "Baja California Sur": "MX-BCS",
    "Campeche": "MX-CAM",
    "Coahuila de Zaragoza": "MX-COA",
    "Colima": "MX-COL",
    "Chiapas": "MX-CHP",
    "Chihuahua": "MX-CHH",
    "Ciudad de México": "MX-CMX",
    "Durango": "MX-DUR",
    "Guanajuato": "MX-GUA",
    "Guerrero": "MX-GRO",
    "Hidalgo": "MX-HID",
    "Jalisco": "MX-JAL",
    "México": "MX-MEX",
    "Michoacán de Ocampo": "MX-MIC",
    "Morelos": "MX-MOR",
    "Nayarit": "MX-NAY",
    "Nuevo León": "MX-NLE",
    "Oaxaca": "MX-OAX",
    "Puebla": "MX-PUE",
    "Querétaro": "MX-QUE",
    "Quintana Roo": "MX-ROO",
    "San Luis Potosí": "MX-SLP",
    "Sinaloa": "MX-SIN",
    "Sonora": "MX-SON",
    "Tabasco": "MX-TAB",
    "Tamaulipas": "MX-TAM",
    "Tlaxcala": "MX-TLA",
    "Veracruz de Ignacio de la Llave": "MX-VER",
    "Yucatán": "MX-YUC",
    "Zacatecas": "MX-ZAC",
}

FORBIDDEN_IN_VIEW = (
    r"SELECT\s+\*",
    r"\bDISTINCT\b",
    r"\bGROUP\s+BY\b",
    r"\bHAVING\b",
    r"\bORDER\s+BY\b",
    r"\bLIMIT\b",
    r"\bWHERE\b",
    r"\bQUALIFY\b",
    r"\bOVER\b",
    r"\b(SUM|COUNT|COUNTIF|AVG|MIN|MAX|ANY_VALUE|ARRAY_AGG|STRING_AGG)\s*\(",
    r"\bROUND\s*\(",
    r"\bSAFE_DIVIDE\s*\(",
    r"\b(SAFE_)?CAST\s*\(",
    r"\bTRIM\s*\(",
    r"\bREGEXP_\w+\s*\(",
    r"\bUSING\b",
    r"\b(LEFT|RIGHT|FULL|CROSS)\s+(OUTER\s+)?JOIN\b",
)


@pytest.fixture
def view_statement(ddl):
    return next(s for s in ddl.statements if s.kind == "create_view")


@pytest.fixture
def view_code(view_statement):
    return " ".join(strip_comments_and_strings(view_statement.text).split())


def test_one_view_between_the_tables_and_the_queries(ddl):
    kinds = [s.kind for s in ddl.statements]
    assert kinds.count("create_view") == 1
    position = kinds.index("create_view")
    assert all(k != "create_table" for k in kinds[position + 1 :])
    assert all(k != "query" for k in kinds[:position])


def test_create_or_replace_without_if_not_exists(view_code):
    assert view_code.upper().startswith(f"CREATE OR REPLACE VIEW {VIEW_REF.upper()} (")
    assert "IF NOT EXISTS" not in view_code.upper()


def test_reference_is_dataset_qualified_without_project(view_statement, view_code):
    assert view_statement.target == VIEW_REF
    assert not re.search(r"[\w`-]+\.farma_analytics\.", view_code)
    for ref in re.finditer(r"\bfarma_analytics\.(\w+)", view_code):
        assert ref.group(1) in {"v_compras_farma_completa", "COMPRAS", "CLUE_CAT", "CUADRO_BASICO"}


def test_columns_names_order_and_types(ddl):
    assert [(c.name, c.type) for c in ddl.view.columns] == EXPECTED


def test_column_names_are_unique_upper_snake_case(ddl):
    names = [c.name for c in ddl.view.columns]
    assert len({n.upper() for n in names}) == len(names)
    assert all(re.fullmatch(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)*", n) for n in names)


def test_view_and_columns_have_descriptions(ddl):
    texts = [ddl.view.description, *(c.description for c in ddl.view.columns)]
    assert all(text.strip() for text in texts)
    assert not any("'" in text or ";" in text for text in texts)


def test_no_expiration(view_code):
    assert "EXPIRATION_TIMESTAMP" not in view_code.upper()


def test_from_and_join_order(view_code):
    from_clause = view_code[view_code.upper().rindex(" FROM ") :]
    assert from_clause.strip() == (
        "FROM farma_analytics.COMPRAS AS compras"
        " INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico"
        " ON compras.CLAVE = cuadro_basico.CLAVE"
        " INNER JOIN farma_analytics.CLUE_CAT AS clue_cat"
        " ON compras.CLUE = clue_cat.CLUE"
    )


def test_every_column_is_qualified_with_a_semantic_alias(ddl):
    code = strip_comments_and_strings(ddl.view.query)
    select_list = code[: code.upper().rindex("FROM ")]
    for name in re.findall(r"(?<![\w.])([A-Za-z_]\w*)\.([A-Z_]+)\b", select_list):
        assert name[0] in {"compras", "clue_cat", "cuadro_basico"}, name


@pytest.mark.parametrize("pattern", FORBIDDEN_IN_VIEW)
def test_forbidden_constructs(ddl, pattern):
    code = strip_comments_and_strings(ddl.view.query)
    assert not re.search(pattern, code, re.IGNORECASE), pattern


def test_iso_mapping_covers_the_32_official_entities(ddl, repo_root):
    query = ddl.view.query
    case = query[query.index("CASE clue_cat.ENTIDAD") : query.index("END AS ENTIDAD_ISO")]
    assert "ELSE" not in strip_comments_and_strings(case).upper()
    mapping = dict(re.findall(r"WHEN '([^']+)' THEN '([^']+)'", case))
    assert len(re.findall(r"\bWHEN\b", case)) == 32
    assert mapping == ISO_3166_2_MX
    reference = repo_root / "generator" / "reference" / "entidades.csv"
    with reference.open(encoding="utf-8") as handle:
        assert {row["entidad"] for row in csv.DictReader(handle)} == set(ISO_3166_2_MX)
