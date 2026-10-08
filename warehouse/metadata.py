"""Comparison of the published dataset and tables with the DDL, using bq show (no job)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence

from warehouse import bq
from warehouse.ddl import DatasetSpec, TableSpec
from warehouse.results import CheckResult

CHECK = "esquema_ddl"

# Legacy type names returned by the tables API.
_TYPE_ALIASES = {"INTEGER": "INT64", "FLOAT": "FLOAT64", "BOOLEAN": "BOOL", "RECORD": "STRUCT"}

Show = Callable[[str], bq.BqResult]


def _diff(objeto: str, detalle: str, esperado: object, obtenido: object) -> CheckResult:
    return CheckResult(CHECK, objeto, detalle, str(esperado), str(obtenido))


def _read(show: Show, ref: str) -> tuple[dict | None, CheckResult | None]:
    result = show(ref)
    if result.ok:
        return json.loads(result.stdout), None
    if "not found" in result.output.lower():
        return None, _diff(ref, f"Falta {ref}: ejecuta 'make bq-schema'", "existe", "no existe")
    return None, _diff(ref, "bq show falló", "respuesta de bq show", result.output)


def _compare_table(table: TableSpec, published: dict) -> list[CheckResult]:
    diffs: list[CheckResult] = []
    if published.get("description", "") != table.description:
        diffs.append(
            _diff(
                table.name,
                "descripción de la tabla",
                table.description,
                published.get("description", ""),
            )
        )
    fields = published.get("schema", {}).get("fields", [])
    for position in range(max(len(table.columns), len(fields))):
        expected = table.columns[position] if position < len(table.columns) else None
        field = fields[position] if position < len(fields) else None
        if field is None:
            diffs.append(_diff(f"{table.name}.{expected.name}", "columna", "existe", "falta"))
            continue
        if expected is None:
            diffs.append(_diff(f"{table.name}.{field['name']}", "columna", "no existe", "sobra"))
            continue
        objeto = f"{table.name}.{expected.name}"
        if field["name"] != expected.name:
            diffs.append(
                _diff(objeto, f"nombre en la posición {position + 1}", expected.name, field["name"])
            )
            continue
        field_type = _TYPE_ALIASES.get(field["type"], field["type"])
        if field_type != expected.type:
            diffs.append(_diff(objeto, "tipo", expected.type, field_type))
        mode = field.get("mode", "NULLABLE")
        if mode != expected.mode:
            diffs.append(_diff(objeto, "modo", expected.mode, mode))
        description = field.get("description", "")
        if description != expected.description:
            diffs.append(_diff(objeto, "descripción", expected.description, description))
    return diffs


def compare(dataset: DatasetSpec, tables: Sequence[TableSpec], show: Show) -> list[CheckResult]:
    """Differences between the DDL and what bq show returns; empty when they match."""
    published, missing = _read(show, dataset.name)
    if missing is not None:
        return [missing]
    diffs: list[CheckResult] = []
    location = published.get("location", "")
    if location.upper() != dataset.location.upper():
        diffs.append(_diff(dataset.name, "location", dataset.location, location))
    if published.get("description", "") != dataset.description:
        diffs.append(
            _diff(
                dataset.name,
                "descripción del dataset",
                dataset.description,
                published.get("description", ""),
            )
        )
    labels = published.get("labels", {})
    if labels != dataset.labels:
        diffs.append(
            _diff(
                dataset.name,
                "labels",
                dict(sorted(dataset.labels.items())),
                dict(sorted(labels.items())),
            )
        )
    for table in tables:
        table_json, missing = _read(show, table.ref)
        if missing is not None:
            diffs.append(missing)
            continue
        diffs.extend(_compare_table(table, table_json))
    return diffs


def verify(dataset: DatasetSpec, tables: Sequence[TableSpec]) -> list[CheckResult]:
    """compare() against the real bq show."""
    return compare(dataset, tables, lambda ref: bq.execute(bq.show(ref)))


def missing_objects(diffs: Sequence[CheckResult]) -> bool:
    """True when the dataset or a table does not exist."""
    return any(d.detalle.startswith("Falta ") for d in diffs)
