"""Figures the Data Studio dashboard must show, computed on the view with the same filters."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from warehouse import bq, queries
from warehouse.results import CheckResult

QUERIES_DIR = bq.REPO_ROOT / "sql" / "dashboard"
QUERY_NAMES = (
    "kpis",
    "kpis_por_anio",
    "gasto_entidad",
    "participacion_institucion",
    "top10_molecula_fabricante",
)
DEFAULT_START = date(2025, 1, 1)
DEFAULT_END = date(2025, 12, 31)
CHECK = "cifras_dashboard"
SHARE_TOLERANCE = Decimal("0.01")
MILLION = Decimal(1_000_000)

# Array parameter of the queries -> visible label of the dashboard control it reproduces.
LISTS = {
    "entidades": "Entidad",
    "instituciones": "Institución",
    "grupos_institucionales": "Grupo institucional",
    "grupos_terapeuticos": "Grupo terapéutico",
    "moleculas": "Molécula",
}

Period = tuple[date, date]
Rows = list[dict]


class FilterError(ValueError):
    """Invalid dashboard filter. The CLI maps it to exit code 2."""


@dataclass(frozen=True)
class Filters:
    """State of the dashboard controls: the Periodo range and the values of each list."""

    desde: date = DEFAULT_START
    hasta: date = DEFAULT_END
    entidades: tuple[str, ...] = ()
    instituciones: tuple[str, ...] = ()
    grupos_institucionales: tuple[str, ...] = ()
    grupos_terapeuticos: tuple[str, ...] = ()
    moleculas: tuple[str, ...] = ()

    def lists(self) -> dict[str, tuple[str, ...]]:
        return {name: getattr(self, name) for name in LISTS}


@dataclass(frozen=True)
class Figures:
    """Answers of the dashboard queries for one filter state."""

    filters: Filters
    reference: Period
    kpis: Mapping
    reference_kpis: Mapping
    years: Rows
    entidades: Rows
    instituciones: Rows
    top10: Rows
    estimated_bytes: tuple[tuple[str, int | None], ...] = ()


def _date(text: str, label: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise FilterError(f"{label}: '{text}' no es una fecha AAAA-MM-DD válida.") from None


def _values(text: str | None, label: str) -> tuple[str, ...]:
    """Comma-separated values of a list control. None or empty means every value."""
    if not text:
        return ()
    values = tuple(value.strip() for value in text.split(","))
    if any(not value for value in values):
        raise FilterError(f"{label}: hay un valor vacío en '{text}'.")
    return values


def build_filters(desde: str, hasta: str, **lists: str | None) -> Filters:
    """Filters from the command line text. Raises FilterError on invalid values."""
    start = _date(desde, "Periodo (desde)")
    end = _date(hasta, "Periodo (hasta)")
    if start > end:
        raise FilterError(f"Periodo: el inicio {start} es posterior al fin {end}.")
    values = {name: _values(lists.get(name), label) for name, label in LISTS.items()}
    return Filters(start, end, **values)


def _year_before(day: date) -> date:
    """Same date one year earlier, with February 29 as February 28."""
    if (day.month, day.day) == (2, 29):
        return date(day.year - 1, 2, 28)
    return day.replace(year=day.year - 1)


def reference_period(start: date, end: date) -> Period:
    """Previous year of Data Studio: the same dates one year earlier."""
    return _year_before(start), _year_before(end)


def parameters(filters: Filters, period: Period | None) -> list[str]:
    """--parameter flags: one ARRAY<STRING> per list and the dates when period is given."""
    params = [
        f"--parameter={name}:ARRAY<STRING>:{json.dumps(list(values), ensure_ascii=False)}"
        for name, values in filters.lists().items()
    ]
    if period is not None:
        params.append(f"--parameter=fecha_inicio:DATE:{period[0].isoformat()}")
        params.append(f"--parameter=fecha_fin:DATE:{period[1].isoformat()}")
    return params


def run(filters: Filters) -> Figures | str:
    """Runs the six dashboard queries. The first error stops the run."""
    period = (filters.desde, filters.hasta)
    reference = reference_period(*period)
    plan = (
        ("kpis", "kpis", period),
        ("kpis (año anterior)", "kpis", reference),
        ("kpis_por_anio", "kpis_por_anio", None),
        ("gasto_entidad", "gasto_entidad", period),
        ("participacion_institucion", "participacion_institucion", period),
        ("top10_molecula_fabricante", "top10_molecula_fabricante", period),
    )
    answers: dict[str, Rows] = {}
    estimates: list[tuple[str, int | None]] = []
    for label, name, dates in plan:
        sql = (QUERIES_DIR / f"{name}.sql").read_text(encoding="utf-8")
        result = queries.run(sql, label, parameters(filters, dates))
        if isinstance(result, str):
            return result
        answers[label] = result.rows
        estimates.append((label, result.estimated_bytes))
    return Figures(
        filters=filters,
        reference=reference,
        kpis=_first(answers["kpis"]),
        reference_kpis=_first(answers["kpis (año anterior)"]),
        years=answers["kpis_por_anio"],
        entidades=answers["gasto_entidad"],
        instituciones=answers["participacion_institucion"],
        top10=answers["top10_molecula_fabricante"],
        estimated_bytes=tuple(estimates),
    )


def _first(rows: Rows) -> dict:
    return rows[0] if rows else {}


def _amount(row: Mapping, column: str) -> Decimal:
    """Exact value of a column, with NULL or a missing value as zero."""
    value = row.get(column)
    return Decimal(0) if value is None else queries.number(value)


def _total(rows: Rows, column: str) -> Decimal:
    return sum((_amount(row, column) for row in rows), Decimal(0))


def change(value: Decimal | None, reference: Decimal | None) -> Decimal | None:
    """Percent change, or None when the reference period has no data."""
    if value is None or not reference:
        return None
    return 100 * (value - reference) / reference


def _diff(rule: str, detail: str, expected: Decimal, obtained: Decimal) -> CheckResult:
    return CheckResult(CHECK, rule, detail, str(expected), str(obtained))


def _calendar_year(period: Period) -> int | None:
    start, end = period
    if start == date(start.year, 1, 1) and end == date(start.year, 12, 31):
        return start.year
    return None


def cross_figures(figures: Figures) -> list[CheckResult]:
    """Differences D1 to D4 between the answers, empty when they all agree."""
    total = _amount(figures.kpis, "IMPORTE")
    diffs = []
    for rule, label, rows in (
        ("D1", "gasto_entidad", figures.entidades),
        ("D2", "participacion_institucion", figures.instituciones),
    ):
        obtained = _total(rows, "IMPORTE")
        if obtained != total:
            diffs.append(_diff(rule, f"{label}: suma de IMPORTE frente a kpis", total, obtained))
    shares = _total(figures.instituciones, "PARTICIPACION_PCT")
    if figures.instituciones and abs(shares - 100) > SHARE_TOLERANCE:
        diffs.append(_diff("D2", "suma de PARTICIPACION_PCT", Decimal(100), shares))
    year = _calendar_year((figures.filters.desde, figures.filters.hasta))
    if year is not None:
        for label, kpis, anio in (
            ("kpis", figures.kpis, year),
            ("kpis (año anterior)", figures.reference_kpis, year - 1),
        ):
            row = next((r for r in figures.years if int(queries.number(r["ANIO"])) == anio), {})
            for column in ("IMPORTE", "PIEZAS"):
                expected, obtained = _amount(row, column), _amount(kpis, column)
                if expected != obtained:
                    detail = f"{label} frente a kpis_por_anio {anio}: {column}"
                    diffs.append(_diff("D3", detail, expected, obtained))
    top = [_amount(row, "IMPORTE") for row in figures.top10]
    if sum(top, Decimal(0)) > total:
        diffs.append(_diff("D4", "suma de IMPORTE del top 10 frente a kpis", total, sum(top)))
    if top != sorted(top, reverse=True):
        diffs.append(_diff("D4", "orden del top 10 por IMPORTE", Decimal(0), Decimal(1)))
    return diffs


def _millions(value: Decimal, places: int) -> str:
    return f"{value / MILLION:,.{places}f}"


def _change_text(value: Decimal | None) -> str:
    return "-" if value is None else f"{value:+.1f} %"


def _filters_text(figures: Figures) -> list[str]:
    filters = figures.filters
    start, end = figures.reference
    lines = [
        f"  Periodo: {filters.desde} a {filters.hasta}",
        f"  Año anterior de las tarjetas: {start} a {end}",
    ]
    for name, label in LISTS.items():
        values = filters.lists()[name]
        lines.append(f"  {label}: {', '.join(values) if values else 'todos los valores'}")
    return lines


# Scorecard title, with its unit, -> column of kpis.sql.
_CARDS = {
    "Monto Total Comprado (M MXN)": "IMPORTE",
    "Total de Piezas Adjudicadas (M piezas)": "PIEZAS",
    "Precio Promedio General por Pieza (MXN por pieza)": "PRECIO_PROMEDIO",
}

# Figures attribute -> title of its text table.
_TITLES = {
    "years": "Totales por año (consulta por año)",
    "entidades": "Gasto por entidad",
    "instituciones": "Participación por institución",
    "top10": "Top 10 pares molécula-fabricante",
}

# Figures attribute -> columns of its text table. IMPORTE_M is the amount in millions.
_COLUMNS = {
    "years": "ANIO FILAS IMPORTE PIEZAS PRECIO_PROMEDIO",
    "entidades": "ENTIDAD ENTIDAD_ISO IMPORTE_M IMPORTE",
    "instituciones": "INSTITUCION IMPORTE_M PARTICIPACION_PCT",
    "top10": "MOLECULA FABRICANTE_COMPRA PIEZAS IMPORTE_M PRECIO_PROMEDIO",
}


def _value(row: Mapping, column: str) -> Decimal | None:
    return None if row.get(column) is None else queries.number(row[column])


def _card_text(column: str, value: Decimal | None) -> str:
    """Scorecard value as the report prints it: millions for amounts and pieces."""
    if value is None:
        return "-"
    if column == "PRECIO_PROMEDIO":
        return f"{value:,.2f}"
    return _millions(value, 1 if column == "IMPORTE" else 2)


def _scorecards(figures: Figures) -> str:
    """Text table of the three scorecards: period, previous year and change."""
    cards = []
    for title, column in _CARDS.items():
        value = _value(figures.kpis, column)
        previous = _value(figures.reference_kpis, column)
        card = {"TARJETA": title, "PERIODO": _card_text(column, value)}
        card["ANIO_ANTERIOR"] = _card_text(column, previous)
        card["CAMBIO"] = _change_text(change(value, previous))
        card["EXACTO"] = "-" if value is None else str(value)
        cards.append(card)
    return queries.format_rows(cards, list(cards[0]))


def _with_millions(rows: Rows) -> Rows:
    """Rows with IMPORTE_M, the amount in millions with one decimal, as the dashboard shows it."""
    return [dict(row, IMPORTE_M=f"{_amount(row, 'IMPORTE') / MILLION:.1f}") for row in rows]


def format_figures(figures: Figures) -> str:
    """Report of the figures the dashboard must show, section by section."""
    sections = ["\n".join(["Filtros del dashboard", *_filters_text(figures)])]
    sections.append("Tarjetas\n" + _scorecards(figures))
    for name, title in _TITLES.items():
        rows = _with_millions(getattr(figures, name))
        sections.append(f"{title}\n{queries.format_rows(rows, _COLUMNS[name].split())}")
    estimates = [
        f"  {label}: {'?' if size is None else size}" for label, size in figures.estimated_bytes
    ]
    sections.append("\n".join(["Bytes estimados", *estimates]))
    return "\n\n".join(sections)


def rules_applied(figures: Figures) -> Sequence[str]:
    """Cross figure rules that apply to these filters. D3 needs a calendar year."""
    base = ["D1", "D2", "D4"]
    period = (figures.filters.desde, figures.filters.hasta)
    return sorted([*base, "D3"]) if _calendar_year(period) is not None else base


def summary(figures: Figures, diffs: Sequence[CheckResult]) -> str:
    applied = rules_applied(figures)
    failed = {d.objeto for d in diffs}
    ok = len([rule for rule in applied if rule not in failed])
    text = f"Cifras cruzadas del dashboard: {ok} de {len(applied)} cuadran."
    if "D3" not in applied:
        text += " D3 no aplica porque el periodo no es un año natural."
    return text
