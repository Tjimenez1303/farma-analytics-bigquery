"""The analytical queries of sql/farma_analytics.sql: run, print and cross-check their answers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from warehouse import bq
from warehouse.ddl import Statement, output_columns
from warehouse.results import CheckResult

QUERY_IDS = ("P1", "P2", "P3", "P3_CATALOGO")
TITLES = {
    "P1": "Las 5 moléculas con más importe",
    "P2": "Institución y entidad con mayor volumen de compra, por importe y por piezas",
    "P3": "Precio promedio por pieza por molécula y fabricante de la compra",
    "P3_CATALOGO": "Precio promedio por pieza por molécula y fabricante de catálogo",
}
TOTALS_SQL = bq.REPO_ROOT / "sql" / "ops" / "totales_vista.sql"
MAX_ROWS = 10000
PREVIEW_ROWS = 20
SHARE_TOLERANCE = Decimal("0.01")
CHECK = "cifras_cruzadas"

Rows = list[dict]


@dataclass(frozen=True)
class QueryResult:
    id: str
    rows: Rows
    estimated_bytes: int | None
    columns: tuple[str, ...] = ()  # SELECT order, since bq --format=json sorts the keys of each row


def number(value: object) -> Decimal:
    """Exact Decimal of a bq value, whether it arrives as text or as a JSON number."""
    return Decimal(str(value))


def run(sql: str, label: str, params: Sequence[str] = ()) -> QueryResult | str:
    """Dry run, then the labeled query, with the same parameters. Returns an error message."""
    dry = bq.execute(bq.dry_run_query(sql, params))
    if not dry.ok:
        return f"{label}: el dry run falló y la consulta no se ejecuta.\n{dry.output}"
    estimate = bq.estimated_bytes(dry.output)
    done = bq.execute(bq.run_query(sql, params, as_json=True, max_rows=MAX_ROWS))
    if not done.ok:
        return f"{label}: la consulta falló.\n{done.output}"
    text = done.stdout.strip()
    rows = json.loads(text, parse_float=Decimal) if text else []
    if len(rows) >= MAX_ROWS:
        return f"{label}: devolvió {MAX_ROWS} filas o más y el resultado podría estar truncado."
    return QueryResult(label, rows, estimate)


def view_totals() -> dict | str:
    """Rows, IMPORTE and PIEZAS of the view, or an error when it fails or the view is empty."""
    result = run(TOTALS_SQL.read_text(encoding="utf-8"), "Totales de la vista")
    if isinstance(result, str):
        return result
    totals = result.rows[0] if result.rows else {"FILAS": 0}
    if number(totals["FILAS"]) == 0:
        return "La vista no tiene filas: ejecuta 'make bq-load'."
    return totals


def run_section(statements: Sequence[Statement]) -> list[QueryResult] | str:
    """The four answers in QUERY_IDS order. The first error stops the run."""
    results: list[QueryResult] = []
    for query_id, statement in zip(QUERY_IDS, statements, strict=True):
        result = run(statement.text, query_id)
        if isinstance(result, str):
            return result
        columns = tuple(output_columns(statement.text))
        results.append(QueryResult(result.id, result.rows, result.estimated_bytes, columns))
    return results


def format_rows(rows: Rows, columns: Sequence[str]) -> str:
    """Text table with numbers right-aligned and NULL for missing values."""
    cells = [["NULL" if row.get(c) is None else str(row[c]) for c in columns] for row in rows]
    numeric = [all(_is_number(r[i]) for r in cells) for i in range(len(columns))]
    widths = [max(len(c), *(len(r[i]) for r in cells)) for i, c in enumerate(columns)]

    def line(values: list[str]) -> str:
        parts = [
            v.rjust(w) if n else v.ljust(w) for v, w, n in zip(values, widths, numeric, strict=True)
        ]
        return "  ".join(parts).rstrip()

    return "\n".join([line(columns), *(line(r) for r in cells)])


def _is_number(text: str) -> bool:
    """Whether a cell is a number, also with thousands commas, a % sign, or "-" for no data."""
    if text in ("-", "NULL"):
        return True
    try:
        Decimal(text.replace(",", "").removesuffix(" %"))
    except ArithmeticError:
        return False
    return True


def format_result(result: QueryResult) -> str:
    """Title, row count, estimated bytes and the rows (a preview for long answers)."""
    count = len(result.rows)
    shown = result.rows[:PREVIEW_ROWS]
    estimate = "?" if result.estimated_bytes is None else result.estimated_bytes
    if count > PREVIEW_ROWS:
        detail = f"{count} filas; se muestran {PREVIEW_ROWS}, la consola muestra todas"
    else:
        detail = f"{count} filas"
    header = f"{result.id} {TITLES[result.id]} ({detail}, {estimate} bytes estimados)"
    if not shown:
        return header
    columns = result.columns or tuple(shown[0])
    return f"{header}\n{format_rows(shown, columns)}"


def _diff(rule: str, detail: str, expected: Decimal, obtained: Decimal) -> CheckResult:
    return CheckResult(CHECK, rule, detail, str(expected), str(obtained))


def _sum(rows: Rows, column: str) -> Decimal:
    return sum((number(row[column]) for row in rows), Decimal(0))


def _totals_rule(rule: str, query_id: str, rows: Rows, totals: Mapping) -> list[CheckResult]:
    """C1 and C2: the price answer adds up to the view totals."""
    diffs = []
    for column, total in (("IMPORTE_TOTAL", "IMPORTE"), ("PIEZAS_TOTALES", "PIEZAS")):
        obtained = _sum(rows, column)
        if obtained != number(totals[total]):
            detail = f"{query_id}: suma de {column} frente al total de la vista"
            diffs.append(_diff(rule, detail, number(totals[total]), obtained))
    return diffs


def _top_molecules_rule(p1: Rows, p3: Rows) -> list[CheckResult]:
    """C3: each top molecule equals the sum of its rows in P3."""
    diffs = []
    for row in p1:
        rows = [r for r in p3 if r["MOLECULA"] == row["MOLECULA"]]
        for column in ("IMPORTE_TOTAL", "PIEZAS_TOTALES"):
            expected = _sum(rows, column)
            if number(row[column]) != expected:
                detail = f"P1 {row['MOLECULA']}: {column} frente a sus filas de P3"
                diffs.append(_diff("C3", detail, expected, number(row[column])))
    return diffs


def _share_rule(query_id: str, rows: Rows, column: str, totals: Mapping) -> list[CheckResult]:
    """C4: each share is 100 x value / view total of its measure, within SHARE_TOLERANCE."""
    diffs = []
    for row in rows:
        total = number(totals[row.get("MEDIDA", "IMPORTE")])
        expected = 100 * number(row[column]) / total
        obtained = number(row["PARTICIPACION_PCT"])
        if abs(obtained - expected) > SHARE_TOLERANCE:
            detail = f"{query_id}: participación frente a 100 × valor / total de la vista"
            diffs.append(_diff("C4", detail, expected.quantize(Decimal("0.0001")), obtained))
    return diffs


def _leaders_rule(p2: Rows) -> list[CheckResult]:
    """C5: the institution-entity leader never exceeds the institution or the entity leader."""
    diffs = []
    for measure in sorted({row["MEDIDA"] for row in p2}):
        leaders = {row["NIVEL"]: number(row["VALOR"]) for row in p2 if row["MEDIDA"] == measure}
        pair = leaders.get("INSTITUCION Y ENTIDAD")
        for level in ("INSTITUCION", "ENTIDAD"):
            if pair is not None and level in leaders and pair > leaders[level]:
                detail = f"P2 {measure}: líder de INSTITUCION Y ENTIDAD frente al de {level}"
                diffs.append(_diff("C5", detail, leaders[level], pair))
    return diffs


def cross_figures(results: Mapping[str, Rows], totals: Mapping) -> list[CheckResult]:
    """Differences between the four answers and the view totals, empty when they all agree."""
    return [
        *_totals_rule("C1", "P3", results["P3"], totals),
        *_totals_rule("C2", "P3_CATALOGO", results["P3_CATALOGO"], totals),
        *_top_molecules_rule(results["P1"], results["P3"]),
        *_share_rule("P1", results["P1"], "IMPORTE_TOTAL", totals),
        *_share_rule("P2", results["P2"], "VALOR", totals),
        *_leaders_rule(results["P2"]),
    ]
