"""Rules of contracts/consultas.md on section 4 of sql/farma_analytics.sql."""

import re

import pytest
from sqlfluff.core import Linter

from warehouse.ddl import DDL_PATH, output_columns, strip_comments_and_strings

QUERY_IDS = ("P1", "P2", "P3", "P3_CATALOGO")

# Output columns from data-model.md, in order: query id, then its columns.
OUTPUT = {
    line.split()[0]: line.split()[1:]
    for line in """
P1 MOLECULA PIEZAS_TOTALES IMPORTE_TOTAL PRECIO_PROMEDIO IMPORTE_PROMEDIO_LINEA PARTICIPACION_PCT
P2 MEDIDA NIVEL INSTITUCION ENTIDAD VALOR PARTICIPACION_PCT
P3 MOLECULA FABRICANTE_COMPRA PIEZAS_TOTALES IMPORTE_TOTAL PRECIO_PROMEDIO
P3_CATALOGO MOLECULA FABRICANTE_CATALOGO PIEZAS_TOTALES IMPORTE_TOTAL PRECIO_PROMEDIO
""".strip().splitlines()
}


@pytest.fixture
def queries(ddl):
    return dict(zip(QUERY_IDS, [s for s in ddl.statements if s.kind == "query"], strict=False))


def _code(statement):
    return " ".join(strip_comments_and_strings(statement.text).split())


def _tree(statement):
    return Linter(dialect="bigquery").parse_string(statement.text).tree


def test_four_queries_after_the_view_and_nothing_else(ddl):
    kinds = [s.kind for s in ddl.statements]
    first = kinds.index("query")
    assert kinds[first - 1] == "create_view"
    assert kinds[first:] == ["query"] * 4


def test_each_query_has_a_question_comment(queries):
    lines = DDL_PATH.read_text(encoding="utf-8").splitlines()
    for query_id, statement in queries.items():
        index = statement.line - 2
        while lines[index].startswith("--"):
            index -= 1
        assert lines[index + 1].startswith("-- Question"), query_id


@pytest.mark.parametrize("query_id", QUERY_IDS)
def test_reads_only_the_view(queries, query_id):
    code = _code(queries[query_id])
    references = re.findall(r"\bfarma_analytics\.(\w+)(\s+AS\s+\w+)?", code)
    assert references
    assert all(ref == ("v_compras_farma_completa", " AS vista") for ref in references)
    assert not re.search(r"[\w`-]+\.farma_analytics\.", code)


@pytest.mark.parametrize("query_id", QUERY_IDS)
def test_forbidden_constructs(queries, query_id):
    code = _code(queries[query_id])
    assert not re.search(r"SELECT\s+\*", code, re.IGNORECASE)
    assert not re.search(r"GROUP\s+BY\s+ALL\b", code, re.IGNORECASE)
    assert not re.search(r"GROUP\s+BY\s+\d", code, re.IGNORECASE)
    assert not re.search(r"SELECT\s+DISTINCT", code, re.IGNORECASE)
    assert "|>" not in code
    assert not re.search(r"\bAGG\s*\(", code)


@pytest.mark.parametrize("query_id", QUERY_IDS)
def test_round_and_order_by_only_in_the_final_select(queries, query_id):
    tree = _tree(queries[query_id])
    for cte in tree.recursive_crawl("common_table_expression"):
        functions = {f.raw.upper() for f in cte.recursive_crawl("function_name")}
        assert "ROUND" not in functions, query_id
        orders = list(
            cte.recursive_crawl("orderby_clause", no_recursive_seg_type="window_specification")
        )
        assert orders == [], query_id


@pytest.mark.parametrize("query_id", QUERY_IDS)
def test_ratios_use_safe_divide_and_avg_is_a_simple_mean(queries, query_id):
    code = _code(queries[query_id])
    assert "/" not in code
    for argument in re.findall(r"\bAVG\(([^()]*)\)", code):
        assert re.fullmatch(r"vista\.\w+", argument.strip()), argument


@pytest.mark.parametrize("query_id", QUERY_IDS)
def test_output_columns(queries, query_id):
    assert output_columns(queries[query_id].text) == OUTPUT[query_id]


def test_p1_top_five_by_amount(queries):
    code = _code(queries["P1"])
    assert re.search(r"GROUP BY vista\.MOLECULA\b", code)
    assert "AVG(vista.IMPORTE)" in code
    assert re.search(r"ORDER BY \w+\.IMPORTE_TOTAL DESC, \w+\.MOLECULA ASC LIMIT 5$", code)


def test_p2_leaders_by_level_and_measure(queries):
    code = _code(queries["P2"])
    assert (
        "GROUP BY GROUPING SETS ( (vista.INSTITUCION, vista.ENTIDAD), (vista.INSTITUCION),"
        " (vista.ENTIDAD) )" in code
    )
    assert "UNPIVOT (VALOR FOR MEDIDA IN (IMPORTE, PIEZAS))" in code
    assert re.search(
        r"QUALIFY RANK\(\) OVER \( PARTITION BY [\w.]+, [\w.]+ ORDER BY [\w.]+\.VALOR DESC \) = 1",
        code,
    )


@pytest.mark.parametrize(
    ("query_id", "fabricante"),
    [("P3", "FABRICANTE_COMPRA"), ("P3_CATALOGO", "FABRICANTE_CATALOGO")],
)
def test_p3_price_by_molecule_and_manufacturer(queries, query_id, fabricante):
    code = _code(queries[query_id])
    assert f"GROUP BY vista.MOLECULA, vista.{fabricante}" in code
    assert "SUM(vista.IMPORTE) AS IMPORTE_TOTAL" in code
    assert "SUM(vista.PIEZAS) AS PIEZAS_TOTALES" in code
    assert re.search(r"SAFE_DIVIDE\(\s*\w+\.IMPORTE_TOTAL,\s*\w+\.PIEZAS_TOTALES\s*\)", code)
