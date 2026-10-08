"""Cross-figure rules C1 to C5 of make bq-consultas, on small consistent answers."""

import copy
from decimal import Decimal

import pytest

from warehouse.queries import cross_figures


def _table(text: str) -> list[dict]:
    """Rows of a pipe-separated text table whose first line holds the column names."""
    lines = text.strip().splitlines()
    columns = [c.strip() for c in lines[0].split("|")]
    rows = [[v.strip() or None for v in line.split("|")] for line in lines[1:]]
    return [dict(zip(columns, row, strict=True)) for row in rows]


# Values as text, the way bq --format=json usually prints them.
TOTALS = {"FILAS": "4", "IMPORTE": "1000.00", "PIEZAS": "100"}

P1 = _table("""
MOLECULA | PIEZAS_TOTALES | IMPORTE_TOTAL | PARTICIPACION_PCT
A        | 50             | 600.00        | 60.00
B        | 50             | 400.00        | 40.00
""")
P2 = _table("""
MEDIDA  | NIVEL                 | VALOR  | PARTICIPACION_PCT
IMPORTE | ENTIDAD               | 700.00 | 70.00
IMPORTE | INSTITUCION           | 650.00 | 65.00
IMPORTE | INSTITUCION Y ENTIDAD | 500.00 | 50.00
PIEZAS  | ENTIDAD               | 70     | 70.00
PIEZAS  | INSTITUCION           | 60     | 60.00
PIEZAS  | INSTITUCION Y ENTIDAD | 45     | 45.00
""")
P3 = _table("""
MOLECULA | FABRICANTE_COMPRA | PIEZAS_TOTALES | IMPORTE_TOTAL
A        | F1                | 30             | 450.00
A        | F2                | 20             | 150.00
B        | F1                | 50             | 400.00
""")
P3_CATALOGO = _table("""
MOLECULA | FABRICANTE_CATALOGO | PIEZAS_TOTALES | IMPORTE_TOTAL
A        | R                   | 50             | 600.00
B        | R                   | 50             | 400.00
""")


@pytest.fixture
def results():
    return copy.deepcopy({"P1": P1, "P2": P2, "P3": P3, "P3_CATALOGO": P3_CATALOGO})


def _rules(diffs):
    return {d.objeto for d in diffs}


def test_consistent_answers_have_no_differences(results):
    assert cross_figures(results, TOTALS) == []


def test_numbers_as_json_numbers_are_also_exact(results):
    totals = {"FILAS": 4, "IMPORTE": Decimal("1000.00"), "PIEZAS": 100}
    for row in results["P3"]:
        row["IMPORTE_TOTAL"] = Decimal(row["IMPORTE_TOTAL"])
        row["PIEZAS_TOTALES"] = int(row["PIEZAS_TOTALES"])
    assert cross_figures(results, totals) == []


def test_c1_p3_total_differs_from_the_view(results):
    results["P3"][2]["IMPORTE_TOTAL"] = "400.01"
    assert "C1" in _rules(cross_figures(results, TOTALS))


def test_c2_catalog_total_differs_from_the_view(results):
    results["P3_CATALOGO"][0]["PIEZAS_TOTALES"] = "49"
    assert _rules(cross_figures(results, TOTALS)) == {"C2"}


def test_c3_top_molecule_differs_from_its_p3_rows(results):
    results["P1"][0]["IMPORTE_TOTAL"] = "599.00"
    results["P1"][0]["PARTICIPACION_PCT"] = "59.90"
    assert _rules(cross_figures(results, TOTALS)) == {"C3"}


def test_c4_share_tolerance_is_one_hundredth(results):
    results["P1"][0]["PARTICIPACION_PCT"] = "60.01"
    assert cross_figures(results, TOTALS) == []
    results["P1"][0]["PARTICIPACION_PCT"] = "60.02"
    assert _rules(cross_figures(results, TOTALS)) == {"C4"}
    results["P1"][0]["PARTICIPACION_PCT"] = "60.00"
    results["P2"][4]["PARTICIPACION_PCT"] = "61.00"
    assert _rules(cross_figures(results, TOTALS)) == {"C4"}


def test_c5_combination_leader_above_a_single_dimension_leader(results):
    results["P2"][2]["VALOR"] = "660.00"
    results["P2"][2]["PARTICIPACION_PCT"] = "66.00"
    diffs = cross_figures(results, TOTALS)
    assert _rules(diffs) == {"C5"}
    assert all(d.chequeo == "cifras_cruzadas" for d in diffs)
