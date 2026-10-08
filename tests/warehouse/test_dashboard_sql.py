"""Rules of contracts/verificacion-sql.md on the dashboard verification queries in sql/dashboard/."""

import re

import pytest
from sqlfluff.core import FluffConfig, Linter

from warehouse import dashboard
from warehouse.ddl import output_columns, strip_comments_and_strings

REPO_ROOT = dashboard.QUERIES_DIR.parents[1]

# Output columns from data-model.md, in order: query name, then its columns.
OUTPUT = {
    line.split()[0]: line.split()[1:]
    for line in """
kpis FILAS IMPORTE PIEZAS PRECIO_PROMEDIO
kpis_por_anio ANIO FILAS IMPORTE PIEZAS PRECIO_PROMEDIO
gasto_entidad ENTIDAD ENTIDAD_ISO IMPORTE
participacion_institucion INSTITUCION IMPORTE PARTICIPACION_PCT
top10_molecula_fabricante MOLECULA FABRICANTE_COMPRA PIEZAS IMPORTE PRECIO_PROMEDIO
""".strip().splitlines()
}

# Filter block of the contract, without its last line (the dates).
FILTERS = """
WHERE
    (ARRAY_LENGTH(@entidades) = 0 OR vista.ENTIDAD IN UNNEST(@entidades))
    AND (ARRAY_LENGTH(@instituciones) = 0 OR vista.INSTITUCION IN UNNEST(@instituciones))
    AND (
        ARRAY_LENGTH(@grupos_institucionales) = 0
        OR vista.GRUPO_INSTITUCIONAL IN UNNEST(@grupos_institucionales)
    )
    AND (
        ARRAY_LENGTH(@grupos_terapeuticos) = 0
        OR vista.GRUPO_TERAPEUTICO IN UNNEST(@grupos_terapeuticos)
    )
    AND (ARRAY_LENGTH(@moleculas) = 0 OR vista.MOLECULA IN UNNEST(@moleculas))
""".strip()
DATES = "AND vista.FECHA BETWEEN @fecha_inicio AND @fecha_fin"


def _sql(name: str) -> str:
    return (dashboard.QUERIES_DIR / f"{name}.sql").read_text(encoding="utf-8")


def _code(name: str) -> str:
    """One-line SQL without comments, with no spaces just inside parentheses."""
    code = " ".join(strip_comments_and_strings(_sql(name)).split())
    return re.sub(r"\s+\)", ")", re.sub(r"\(\s+", "(", code))


def _final_select(name: str) -> str:
    """Code after the last CTE, that is the final SELECT."""
    code = _code(name)
    return code[code.rfind(") SELECT") + 2 :] if ") SELECT" in code else code


def test_the_five_files_and_nothing_else():
    assert sorted(p.stem for p in dashboard.QUERIES_DIR.glob("*.sql")) == sorted(OUTPUT)
    assert set(dashboard.QUERY_NAMES) == set(OUTPUT)


@pytest.mark.parametrize("name", OUTPUT)
def test_starts_with_an_english_comment(name):
    first = _sql(name).splitlines()[0]
    assert first.startswith("-- Dashboard ")


@pytest.mark.parametrize("name", OUTPUT)
def test_reads_only_the_view_without_joins(name):
    code = _code(name)
    references = re.findall(r"\bfarma_analytics\.(\w+)(\s+AS\s+\w+)?", code)
    assert references == [("v_compras_farma_completa", " AS vista")]
    assert not re.search(r"[\w`-]+\.farma_analytics\.", code)
    assert " JOIN " not in code


@pytest.mark.parametrize("name", OUTPUT)
def test_same_filter_block_in_a_filtrada_cte(name):
    sql = _sql(name)
    assert sql.startswith(sql.splitlines()[0] + "\nWITH filtrada AS (\n")
    indented = "\n".join("    " + line for line in FILTERS.splitlines())
    assert indented in sql
    dates = f"\n        {DATES}\n)"
    if name == "kpis_por_anio":
        assert "@fecha_inicio" not in sql and "@fecha_fin" not in sql
        assert f"{indented}\n)" in sql
    else:
        assert f"{indented}{dates}" in sql


@pytest.mark.parametrize("name", OUTPUT)
def test_output_columns_in_order(name):
    assert output_columns(_sql(name)) == OUTPUT[name]


@pytest.mark.parametrize("name", OUTPUT)
def test_safe_division_and_no_average(name):
    code = _code(name)
    assert "AVG(" not in code
    if "PRECIO_PROMEDIO" in OUTPUT[name] or "PARTICIPACION_PCT" in OUTPUT[name]:
        assert "SAFE_DIVIDE(" in code
    assert " / " not in code


@pytest.mark.parametrize("name", OUTPUT)
def test_round_and_order_by_only_in_the_final_select(name):
    code = _code(name)
    final = _final_select(name)
    assert code.count("ROUND(") == final.count("ROUND(")
    assert code.count("ORDER BY") == final.count("ORDER BY")
    assert "SELECT *" not in code
    assert not re.search(r"GROUP BY (\d|ALL\b)", code)


# Number of ROUND calls in each final SELECT: only prices (2 decimals) and the share (4 decimals).
ROUNDS = {
    "kpis": 1,
    "kpis_por_anio": 1,
    "gasto_entidad": 0,
    "participacion_institucion": 1,
    "top10_molecula_fabricante": 1,
}


@pytest.mark.parametrize("name", OUTPUT)
def test_only_price_and_share_are_rounded(name):
    final = _final_select(name)
    assert final.count("ROUND(") == ROUNDS[name]
    if "PRECIO_PROMEDIO" in OUTPUT[name]:
        assert re.search(r"ROUND\(SAFE_DIVIDE\(.+?\), 2\) AS PRECIO_PROMEDIO", final)
    if "PARTICIPACION_PCT" in OUTPUT[name]:
        assert re.search(r"ROUND\(100 \* .+?, 4\) AS PARTICIPACION_PCT", final)


def test_top10_order_and_limit():
    assert re.search(
        r"ORDER BY \w+\.IMPORTE DESC, \w+\.MOLECULA ASC, \w+\.FABRICANTE_COMPRA ASC LIMIT 10$",
        _code("top10_molecula_fabricante").rstrip(" ;"),
    )


@pytest.mark.parametrize(
    ("name", "column"), [("gasto_entidad", "ENTIDAD"), ("participacion_institucion", "INSTITUCION")]
)
def test_breakdowns_ordered_by_amount_then_name(name, column):
    assert re.search(rf"ORDER BY \w+\.IMPORTE DESC, \w+\.{column} ASC$", _code(name).rstrip(" ;"))


def test_years_ordered():
    assert re.search(r"ORDER BY \w+\.ANIO ASC$", _code("kpis_por_anio").rstrip(" ;"))


@pytest.mark.parametrize("name", OUTPUT)
def test_lines_fit_100_characters(name):
    assert all(len(line) <= 100 for line in _sql(name).splitlines())


def test_sqlfluff_reports_no_violations():
    linter = Linter(config=FluffConfig.from_path(str(REPO_ROOT)))
    result = linter.lint_paths((str(dashboard.QUERIES_DIR),))
    assert [(r["filepath"], v["code"]) for r in result.as_records() for v in r["violations"]] == []
