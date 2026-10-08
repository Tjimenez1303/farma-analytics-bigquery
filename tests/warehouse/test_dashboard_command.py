"""make bq-dashboard: filters, previous year, dry runs, labels and the cross figures D1 to D4."""

import csv
import json
from datetime import date
from decimal import Decimal

import pytest

from warehouse import bq, commands, dashboard
from warehouse.__main__ import main

VIEW_REF = "farma_analytics.v_compras_farma_completa"
REFERENCE = "fecha_inicio:DATE:2024-01-01"


def _table(text: str) -> list[dict]:
    """Rows of a pipe-separated text table whose first line holds the column names."""
    lines = text.strip().splitlines()
    columns = [c.strip() for c in lines[0].split("|")]
    rows = [[v.strip() or None for v in line.split("|")] for line in lines[1:]]
    return [dict(zip(columns, row, strict=True)) for row in rows]


TOTALS = _table("""
FILAS | IMPORTE | PIEZAS
5     | 1800.00 | 200
""")
KPIS = _table("""
FILAS | IMPORTE | PIEZAS | PRECIO_PROMEDIO
3     | 1000.00 | 100    | 10.00
""")
KPIS_REFERENCE = _table("""
FILAS | IMPORTE | PIEZAS | PRECIO_PROMEDIO
2     | 800.00  | 100    | 8.00
""")
YEARS = _table("""
ANIO | FILAS | IMPORTE | PIEZAS | PRECIO_PROMEDIO
2024 | 2     | 800.00  | 100    | 8.00
2025 | 3     | 1000.00 | 100    | 10.00
""")
ENTITIES = _table("""
ENTIDAD | ENTIDAD_ISO | IMPORTE
Jalisco | MX-JAL      | 600.00
México  | MX-MEX      | 400.00
""")
INSTITUTIONS = _table("""
INSTITUCION | IMPORTE | PARTICIPACION_PCT
IMSS        | 700.00  | 70.0000
ISSSTE      | 300.00  | 30.0000
""")
TOP10 = _table("""
MOLECULA | FABRICANTE_COMPRA | PIEZAS | IMPORTE | PRECIO_PROMEDIO
A        | F                 | 50     | 600.00  | 12.00
B        | G                 | 50     | 400.00  | 8.00
""")

# Answer of each dashboard query, keyed by the first words of its leading comment.
ANSWERS = {
    "-- Dashboard scorecards by year": YEARS,
    "-- Dashboard bar chart and map": ENTITIES,
    "-- Dashboard bar chart of each INSTITUCION": INSTITUTIONS,
    "-- Dashboard table of the 10": TOP10,
}
KPIS_MARKER = "-- Dashboard scorecards: rows"


def _runs(text: str, reference: bool | None = None):
    """Predicate for the run (not the dry run) of a query, optionally by its period."""

    def predicate(command: bq.Command) -> bool:
        if "--dry_run" in command.argv or text not in (command.stdin or ""):
            return False
        is_reference = f"--parameter={REFERENCE}" in command.argv
        return reference is None or is_reference == reference

    return predicate


def _answer(fake, predicate, rows) -> None:
    """Answer the matching run ahead of every other rule."""
    fake.rules.insert(0, (predicate, bq.BqResult(0, json.dumps(rows, ensure_ascii=False), "")))


@pytest.fixture
def answered(fake_bq, published):
    """bq answers: the view exists, its totals and one answer per dashboard query."""
    fake_bq.when(_runs("Rows, IMPORTE and PIEZAS of the view"), stdout=json.dumps(TOTALS))
    fake_bq.when(_runs(KPIS_MARKER, reference=True), stdout=json.dumps(KPIS_REFERENCE))
    fake_bq.when(_runs(KPIS_MARKER, reference=False), stdout=json.dumps(KPIS))
    for marker, rows in ANSWERS.items():
        fake_bq.when(_runs(marker), stdout=json.dumps(rows, ensure_ascii=False))
    fake_bq.answer_show(published)
    return fake_bq


def _queries(fake):
    return [c for c in fake.calls if "query" in c.argv]


def _params(command: bq.Command) -> list[str]:
    return [a for a in command.argv if a.startswith("--parameter=")]


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2025, 1, 1), date(2025, 12, 31), (date(2024, 1, 1), date(2024, 12, 31))),
        (date(2025, 3, 1), date(2025, 3, 31), (date(2024, 3, 1), date(2024, 3, 31))),
        (date(2024, 7, 1), date(2025, 6, 30), (date(2023, 7, 1), date(2024, 6, 30))),
        (date(2024, 2, 29), date(2024, 2, 29), (date(2023, 2, 28), date(2023, 2, 28))),
    ],
)
def test_reference_period_is_the_same_dates_a_year_before(start, end, expected):
    assert dashboard.reference_period(start, end) == expected


def test_default_filters_are_2025_and_every_value():
    filters = dashboard.build_filters("2025-01-01", "2025-12-31")
    assert (filters.desde, filters.hasta) == (date(2025, 1, 1), date(2025, 12, 31))
    assert all(values == () for values in filters.lists().values())


def test_lists_split_on_commas_and_keep_accents():
    filters = dashboard.build_filters(
        "2025-01-01", "2025-12-31", entidades="Jalisco, Michoacán de Ocampo"
    )
    assert filters.entidades == ("Jalisco", "Michoacán de Ocampo")


@pytest.mark.parametrize(
    ("desde", "hasta", "lists"),
    [
        ("2025-13-01", "2025-12-31", {}),
        ("2025-12-31", "2025-01-01", {}),
        ("2025-01-01", "2025-12-31", {"moleculas": "Paracetamol,,Aciclovir"}),
    ],
)
def test_invalid_filters_raise(desde, hasta, lists):
    with pytest.raises(dashboard.FilterError):
        dashboard.build_filters(desde, hasta, **lists)


def test_parameters_are_dates_and_json_arrays():
    filters = dashboard.build_filters("2025-01-01", "2025-12-31", entidades="Michoacán de Ocampo")
    params = dashboard.parameters(filters, (filters.desde, filters.hasta))
    assert '--parameter=entidades:ARRAY<STRING>:["Michoacán de Ocampo"]' in params
    assert "--parameter=moleculas:ARRAY<STRING>:[]" in params
    assert "--parameter=fecha_inicio:DATE:2025-01-01" in params
    assert "--parameter=fecha_fin:DATE:2025-12-31" in params
    without_dates = dashboard.parameters(filters, None)
    assert not any("fecha_" in p for p in without_dates)


def test_invalid_dates_stop_before_bq(warehouse_env, fake_bq, capsys):
    assert main(["dashboard", "--desde", "2025-02-30"]) == 2
    assert fake_bq.calls == []
    assert "Periodo" in capsys.readouterr().err


def test_each_query_runs_after_its_dry_run_with_labels(warehouse_env, answered, capsys):
    assert commands.run_dashboard(dashboard.Filters()) == 0
    calls = _queries(answered)
    assert len(calls) == 2 * 7
    for dry, run in zip(calls[::2], calls[1::2], strict=True):
        assert "--dry_run" in dry.argv and "--dry_run" not in run.argv
        assert dry.stdin == run.stdin
        assert _params(dry) == _params(run)
        assert any(a.startswith("--label=") for a in run.argv)
        assert not any(a.startswith(("--location", "--maximum_bytes_billed")) for a in run.argv)
    kpis = [c for c in calls[1::2] if KPIS_MARKER in c.stdin]
    assert [f"--parameter={REFERENCE}" in c.argv for c in kpis] == [False, True]
    out = capsys.readouterr().out
    assert "2024-01-01 a 2024-12-31" in out
    assert "+25.0 %" in out
    assert "Cifras cruzadas del dashboard: 4 de 4 cuadran." in out


def test_yearly_query_has_no_date_parameters(warehouse_env, answered):
    commands.run_dashboard(dashboard.Filters())
    yearly = [c for c in _queries(answered) if "-- Dashboard scorecards by year" in c.stdin]
    assert yearly and all(not any("fecha_" in p for p in _params(c)) for c in yearly)


def test_failed_dry_run_stops_that_query(warehouse_env, answered, capsys):
    marker = "-- Dashboard table of the 10"
    answered.rules.insert(0, (answered.dry_run(marker), bq.BqResult(1, "", "Syntax error")))
    assert commands.run_dashboard(dashboard.Filters()) == 1
    assert not any(_runs(marker)(c) for c in answered.calls)
    assert "Syntax error" in capsys.readouterr().out


def test_missing_view_stops_before_any_query(warehouse_env, fake_bq, published, capsys):
    fake_bq.missing(VIEW_REF)
    fake_bq.answer_show(published)
    assert commands.run_dashboard(dashboard.Filters()) == 1
    assert _queries(fake_bq) == []
    assert f"Falta {VIEW_REF}: ejecuta 'make bq-vista'" in capsys.readouterr().out


def test_empty_view_stops_before_the_dashboard_queries(warehouse_env, answered, capsys):
    _answer(answered, _runs("Rows, IMPORTE and PIEZAS of the view"), [dict(TOTALS[0], FILAS="0")])
    assert commands.run_dashboard(dashboard.Filters()) == 1
    assert len(_queries(answered)) == 2
    assert "La vista no tiene filas: ejecuta 'make bq-load'." in capsys.readouterr().out


def _figures(**changes) -> dashboard.Figures:
    """Consistent figures of the default 2025 state, with some parts replaced."""
    base = {
        "filters": dashboard.Filters(),
        "reference": (date(2024, 1, 1), date(2024, 12, 31)),
        "kpis": KPIS[0],
        "reference_kpis": KPIS_REFERENCE[0],
        "years": YEARS,
        "entidades": ENTITIES,
        "instituciones": INSTITUTIONS,
        "top10": TOP10,
    }
    return dashboard.Figures(**{**base, **changes})


def _rules(diffs) -> list[str]:
    return [d.objeto for d in diffs]


def test_consistent_figures_have_no_differences():
    assert dashboard.cross_figures(_figures()) == []


def test_d1_entities_must_add_up_to_the_scorecard():
    entities = [dict(ENTITIES[0], IMPORTE="500.00"), ENTITIES[1]]
    assert _rules(dashboard.cross_figures(_figures(entidades=entities))) == ["D1"]


def test_d2_institutions_and_their_shares():
    shares = [dict(INSTITUTIONS[0], PARTICIPACION_PCT="70.0200"), INSTITUTIONS[1]]
    assert _rules(dashboard.cross_figures(_figures(instituciones=shares))) == ["D2"]
    within = [dict(INSTITUTIONS[0], PARTICIPACION_PCT="70.0050"), INSTITUTIONS[1]]
    assert dashboard.cross_figures(_figures(instituciones=within)) == []


def test_d3_full_year_matches_the_yearly_query():
    years = [YEARS[0], dict(YEARS[1], IMPORTE="999.00")]
    assert _rules(dashboard.cross_figures(_figures(years=years))) == ["D3"]


def test_d3_previous_year_matches_the_yearly_query():
    reference = dict(KPIS_REFERENCE[0], PIEZAS="99")
    assert _rules(dashboard.cross_figures(_figures(reference_kpis=reference))) == ["D3"]


def test_d3_skipped_when_the_period_is_not_a_calendar_year():
    years = [YEARS[0], dict(YEARS[1], IMPORTE="999.00")]
    filters = dashboard.Filters(desde=date(2025, 1, 1), hasta=date(2025, 6, 30))
    assert dashboard.cross_figures(_figures(years=years, filters=filters)) == []


def test_d3_year_without_rows_counts_as_zero():
    empty = {"FILAS": "0", "IMPORTE": None, "PIEZAS": None, "PRECIO_PROMEDIO": None}
    filters = dashboard.Filters(desde=date(2023, 1, 1), hasta=date(2023, 12, 31))
    figures = _figures(
        filters=filters, kpis=empty, reference_kpis=empty, entidades=[], instituciones=[], top10=[]
    )
    assert dashboard.cross_figures(figures) == []


def test_d4_top10_within_the_total_and_ordered():
    larger = [dict(TOP10[0], IMPORTE="900.00"), dict(TOP10[1], IMPORTE="200.00")]
    assert _rules(dashboard.cross_figures(_figures(top10=larger))) == ["D4"]
    unordered = [TOP10[1], TOP10[0]]
    assert _rules(dashboard.cross_figures(_figures(top10=unordered))) == ["D4"]


def test_change_is_empty_without_reference_data():
    assert dashboard.change(Decimal(10), None) is None
    assert dashboard.change(Decimal(10), Decimal(0)) is None
    assert dashboard.change(Decimal(125), Decimal(100)) == Decimal(25)


@pytest.mark.parametrize(
    ("path", "columns"),
    [
        ("entidades.csv", ["entidad"]),
        ("instituciones.csv", ["institucion", "grupo_institucional"]),
        ("moleculas.csv", ["molecula", "grupo_terapeutico"]),
    ],
)
def test_catalog_values_have_no_commas(path, columns):
    reference = dashboard.QUERIES_DIR.parents[1] / "generator" / "reference" / path
    with reference.open(encoding="utf-8") as handle:
        values = [row[c] for row in csv.DictReader(handle) for c in columns]
    assert values and all("," not in v for v in values)


def test_make_help_lists_the_target():
    makefile = (dashboard.QUERIES_DIR.parents[1] / "Makefile").read_text(encoding="utf-8")
    assert (
        "bq-dashboard: require-venv require-project ## Calcula sobre la vista las cifras que "
        "muestra el dashboard (KPIs, entidades, instituciones y top 10) con los filtros indicados"
    ) in makefile
