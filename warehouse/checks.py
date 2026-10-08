"""Quality checks of sql/checks/, their negative cases and the content fingerprint."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from warehouse import bq
from warehouse.ddl import TableSpec, ViewSpec, strip_comments_and_strings
from warehouse.expectations import Parameter, as_bq_parameters
from warehouse.results import CheckResult, format_table, from_row

CHECKS_DIR = bq.REPO_ROOT / "sql" / "checks"
NEGATIVE_DIR = CHECKS_DIR / "negativos"
FINGERPRINT_SQL = bq.REPO_ROOT / "sql" / "ops" / "huella_contenido.sql"
MAX_ROWS = 1000

_PARAMETER = re.compile(r"@([a-z_]+)")
_TABLE_REF = re.compile(rf"\b{bq.DATASET}\.(\w+)(?=\s+AS\s)")
VIEW_REF = f"{bq.DATASET}.v_compras_farma_completa"
VIEW_MISSING = "La vista no está desplegada: ejecuta 'make bq-vista'."

Relation = TableSpec | ViewSpec


@dataclass(frozen=True)
class QueryOutcome:
    ok: bool
    rows: list[dict]
    estimated_bytes: int | None
    error: str


def check_files(directory: Path = CHECKS_DIR) -> list[Path]:
    return sorted(Path(directory).glob("*.sql"))


def check_name(path: Path) -> str:
    """01_conteo_filas.sql -> conteo_filas."""
    return Path(path).stem.split("_", 1)[1]


def references_view(sql: str) -> bool:
    """True when the SQL reads the view outside comments and string literals."""
    return re.search(rf"\b{re.escape(VIEW_REF)}\b", strip_comments_and_strings(sql)) is not None


def referenced_parameters(sql: str) -> list[str]:
    """Named parameters used outside comments and string literals, sorted."""
    return sorted(set(_PARAMETER.findall(strip_comments_and_strings(sql))))


def _rows(stdout: str) -> list[dict]:
    text = stdout.strip()
    return json.loads(text) if text else []


def run_checked_query(sql: str, params: Sequence[str] = ()) -> QueryOutcome:
    """Dry run, then the labeled query with JSON output. Nothing runs if the dry run fails."""
    dry = bq.execute(bq.dry_run_query(sql, params))
    if not dry.ok:
        return QueryOutcome(False, [], None, f"el dry run falló: {dry.output}")
    estimate = bq.estimated_bytes(dry.output)
    result = bq.execute(bq.run_query(sql, params, as_json=True, max_rows=MAX_ROWS))
    if not result.ok:
        return QueryOutcome(False, [], estimate, f"la consulta falló: {result.output}")
    return QueryOutcome(True, _rows(result.stdout), estimate, "")


def _bytes_label(estimate: int | None) -> str:
    return "bytes estimados desconocidos" if estimate is None else f"{estimate} bytes estimados"


def _count_label(rows: list[dict]) -> str:
    return f"{MAX_ROWS} o más" if len(rows) >= MAX_ROWS else str(len(rows))


def run_sql_checks(
    expectations: dict[str, Parameter], include_view: bool = True
) -> tuple[int, int, list[CheckResult]]:
    """(passed, total, failing rows) of the checks in sql/checks/, printing one line each.

    With include_view=False the checks that read the view are left out of the run and the total.
    """
    files = check_files()
    if not include_view:
        skipped = [p for p in files if references_view(p.read_text(encoding="utf-8"))]
        files = [p for p in files if p not in skipped]
        if skipped:
            print(VIEW_MISSING)
    passed = 0
    failures: list[CheckResult] = []
    for path in files:
        sql = path.read_text(encoding="utf-8")
        params = as_bq_parameters(expectations, referenced_parameters(sql))
        outcome = run_checked_query(sql, params)
        name = check_name(path)
        if not outcome.ok:
            print(f"FALLO {name}: {outcome.error}")
            continue
        if outcome.rows:
            results = [from_row(row) for row in outcome.rows]
            failures.extend(results)
            print(
                f"FALLO {name}: {_count_label(outcome.rows)} filas "
                f"({_bytes_label(outcome.estimated_bytes)})"
            )
            print(format_table(results))
            continue
        passed += 1
        print(f"OK    {name}: 0 filas ({_bytes_label(outcome.estimated_bytes)})")
    return passed, len(files), failures


def run_fingerprint() -> int:
    """Rows and content fingerprint per table, to compare two loads."""
    outcome = run_checked_query(FINGERPRINT_SQL.read_text(encoding="utf-8"))
    if not outcome.ok:
        print(f"Huella de contenido: {outcome.error}")
        return 1
    print(f"Huella de contenido ({_bytes_label(outcome.estimated_bytes)}):")
    rows = [(r["TABLA"], str(r["FILAS"]), str(r["HUELLA"])) for r in outcome.rows]
    table = [("TABLA", "FILAS", "HUELLA"), *rows]
    widths = [max(len(row[i]) for row in table) for i in range(3)]
    for row in table:
        print("  ".join(v.ljust(w) for v, w in zip(row, widths, strict=True)).rstrip())
    return 0


def load_negative_case(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _literal(value: str | None, sql_type: str) -> str:
    if value is None:
        return f"CAST(NULL AS {sql_type})"
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"CAST('{escaped}' AS {sql_type})"


def _inline_select(table: Relation, rows: list[dict]) -> str:
    columns = ", ".join(c.name for c in table.columns)
    struct = ", ".join(f"{c.name} {c.type}" for c in table.columns)
    values = ", ".join(
        "(" + ", ".join(_literal(row[c.name], c.type) for c in table.columns) + ")" for row in rows
    )
    return f"(SELECT {columns} FROM UNNEST(ARRAY<STRUCT<{struct}>>[{values}]))"


def inline_tables(sql: str, case: dict, relations: Sequence[Relation]) -> str:
    """The check with each farma_analytics.<TABLE or VIEW> AS <alias> replaced by the case rows."""
    by_name = {r.name: r for r in relations}

    def replace(match: re.Match) -> str:
        relation = by_name[match.group(1)]
        if relation.name not in case["tablas"]:
            raise ValueError(f"El caso no trae filas para {relation.name}.")
        return _inline_select(relation, case["tablas"][relation.name])

    inlined = _TABLE_REF.sub(replace, sql)
    if f"{bq.DATASET}." in strip_comments_and_strings(inlined):
        raise ValueError("Queda una referencia a una tabla real sin sustituir.")
    return inlined


def run_negative_checks(expectations: dict[str, Parameter], relations: Sequence[Relation]) -> int:
    """0 when every check reports its expected object for its negative case."""
    files = check_files()
    detected = 0
    for path in files:
        name = check_name(path)
        case = load_negative_case(NEGATIVE_DIR / f"{path.stem}.json")
        sql = inline_tables(path.read_text(encoding="utf-8"), case, relations)
        params = as_bq_parameters(expectations, referenced_parameters(sql))
        outcome = run_checked_query(sql, params)
        expected = case["esperado"]
        found = outcome.ok and any(
            row.get("CHEQUEO") == expected["CHEQUEO"] and row.get("OBJETO") == expected["OBJETO"]
            for row in outcome.rows
        )
        if found:
            detected += 1
            print(
                f"OK    {name}: detectó el error en {expected['OBJETO']} "
                f"({_bytes_label(outcome.estimated_bytes)})"
            )
        else:
            reason = outcome.error or f"{len(outcome.rows)} filas sin {expected['OBJETO']}"
            print(f"FALLO {name}: NO detectó el error ({reason})")
    print(f"Casos negativos: {detected} de {len(files)} detectados.")
    return 0 if files and detected == len(files) else 1
