"""make bq-consultas: view totals, the four queries after their dry runs and the cross figures."""

import json

import pytest

from warehouse import bq, commands, queries

VIEW_REF = "farma_analytics.v_compras_farma_completa"


def _table(text: str) -> list[dict]:
    """Rows of a pipe-separated text table whose first line holds the column names."""
    lines = text.strip().splitlines()
    columns = [c.strip() for c in lines[0].split("|")]
    rows = [[v.strip() or None for v in line.split("|")] for line in lines[1:]]
    return [dict(zip(columns, row, strict=True)) for row in rows]


TOTALS = _table("""
FILAS  | IMPORTE | PIEZAS
298500 | 1000.00 | 100
""")

# Answer of each query, keyed by a text that only that query contains.
ANSWERS = {
    "LIMIT 5": _table("""
MOLECULA | PIEZAS_TOTALES | IMPORTE_TOTAL | PRECIO_PROMEDIO | PARTICIPACION_PCT
A        | 50             | 600.00        | 12.00           | 60.00
"""),
    "UNPIVOT": _table("""
MEDIDA  | NIVEL   | INSTITUCION | ENTIDAD | VALOR  | PARTICIPACION_PCT
IMPORTE | ENTIDAD |             | Jalisco | 600.00 | 60.00
"""),
    "vista.FABRICANTE_COMPRA": _table("""
MOLECULA | FABRICANTE_COMPRA | PIEZAS_TOTALES | IMPORTE_TOTAL | PRECIO_PROMEDIO
A        | F                 | 50             | 600.00        | 12.00
B        | F                 | 50             | 400.00        | 8.00
"""),
    "vista.FABRICANTE_CATALOGO": _table("""
MOLECULA | FABRICANTE_CATALOGO | PIEZAS_TOTALES | IMPORTE_TOTAL | PRECIO_PROMEDIO
A        | R                   | 100            | 1000.00       | 10.00
"""),
}
P3_MARKER = "vista.FABRICANTE_COMPRA"


def _answer(fake, marker: str, rows: list[dict]) -> None:
    """Answer the run of the query that contains marker, ahead of every other rule."""
    fake.rules.insert(0, (fake.query_run(marker), bq.BqResult(0, json.dumps(rows), "")))


@pytest.fixture
def answered(fake_bq, published):
    """bq answers: the view exists, its totals and one answer per query."""
    fake_bq.when(fake_bq.query_run("AS FILAS"), stdout=json.dumps(TOTALS))
    for marker, rows in ANSWERS.items():
        fake_bq.when(fake_bq.query_run(marker), stdout=json.dumps(rows))
    fake_bq.answer_show(published)
    return fake_bq


def _queries(fake):
    return [c for c in fake.calls if "query" in c.argv]


def test_totals_first_then_each_query_after_its_dry_run(warehouse_env, answered, ddl, capsys):
    assert commands.run_queries() == 0
    calls = _queries(answered)
    assert "AS FILAS" in calls[0].stdin and "--dry_run" in calls[0].argv
    assert "AS FILAS" in calls[1].stdin and "--dry_run" not in calls[1].argv
    statements = [s.text for s in ddl.statements if s.kind == "query"]
    rest = calls[2:]
    assert len(rest) == 2 * len(statements)
    for dry, run, text in zip(rest[::2], rest[1::2], statements, strict=True):
        assert dry.stdin == run.stdin == text
        assert "--dry_run" in dry.argv
        assert f"--max_rows={queries.MAX_ROWS}" in run.argv
        assert "--format=json" in run.argv
        assert any(a.startswith("--label=") for a in run.argv)
    out = capsys.readouterr().out
    assert "P1 Las 5 moléculas con más importe (1 filas" in out
    assert "Cifras cruzadas: 5 de 5 cuadran." in out


def test_columns_follow_the_select_order_not_the_json_order(warehouse_env, answered, capsys):
    rows = [dict(sorted(row.items())) for row in ANSWERS["LIMIT 5"]]
    _answer(answered, "LIMIT 5", rows)
    commands.run_queries()
    out = capsys.readouterr().out
    header = next(line for line in out.splitlines() if line.startswith("MOLECULA"))
    assert header.split() == [
        "MOLECULA",
        "PIEZAS_TOTALES",
        "IMPORTE_TOTAL",
        "PRECIO_PROMEDIO",
        "IMPORTE_PROMEDIO_LINEA",
        "PARTICIPACION_PCT",
    ]


def test_missing_view_stops_before_any_query(warehouse_env, fake_bq, published, capsys):
    fake_bq.missing(VIEW_REF)
    fake_bq.answer_show(published)
    assert commands.run_queries() == 1
    assert _queries(fake_bq) == []
    assert f"Falta {VIEW_REF}: ejecuta 'make bq-vista'" in capsys.readouterr().out


def test_empty_view_stops_before_the_questions(warehouse_env, answered, capsys):
    _answer(answered, "AS FILAS", [dict(TOTALS[0], FILAS="0")])
    assert commands.run_queries() == 1
    assert len(_queries(answered)) == 2
    assert "La vista no tiene filas: ejecuta 'make bq-load'." in capsys.readouterr().out


def test_failed_dry_run_names_the_query(warehouse_env, answered, capsys):
    answered.rules.insert(0, (answered.dry_run("UNPIVOT"), bq.BqResult(1, "", "Syntax error")))
    assert commands.run_queries() == 1
    assert not any(answered.query_run("UNPIVOT")(c) for c in answered.calls)
    out = capsys.readouterr().out
    assert "P2" in out and "Syntax error" in out


def test_possible_truncation_fails(warehouse_env, answered, capsys):
    _answer(answered, P3_MARKER, ANSWERS[P3_MARKER][:1] * queries.MAX_ROWS)
    assert commands.run_queries() == 1
    assert "truncado" in capsys.readouterr().out


def test_long_answers_show_a_preview(warehouse_env, answered, capsys):
    rows = [dict(ANSWERS[P3_MARKER][0], MOLECULA=f"M{i:02d}") for i in range(25)]
    _answer(answered, P3_MARKER, rows)
    commands.run_queries()
    out = capsys.readouterr().out
    assert "(25 filas; se muestran 20, la consola muestra todas" in out
    assert "M19" in out and "M20" not in out


def test_cross_figure_difference_fails(warehouse_env, answered, capsys):
    _answer(answered, "AS FILAS", [dict(TOTALS[0], IMPORTE="999.00")])
    assert commands.run_queries() == 1
    out = capsys.readouterr().out
    assert "cifras_cruzadas" in out
    assert "Cifras cruzadas: " in out and "5 de 5" not in out
