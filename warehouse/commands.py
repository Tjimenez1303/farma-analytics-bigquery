"""Orchestration of the schema, vista, load, checks, checks-negativos and consultas commands."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from generator.manifest import verify as verify_csv
from warehouse import bq, checks, metadata, queries
from warehouse.ddl import Ddl, DdlError, parse_file, write_load_schemas
from warehouse.expectations import MANIFEST_PATH, Parameter, load_expectations
from warehouse.results import format_table

_LABELS = {
    "create_schema": "CREATE SCHEMA",
    "create_table": "CREATE TABLE",
    "create_view": "CREATE OR REPLACE VIEW",
}


def _environment() -> Ddl | int:
    """Parsed DDL, or an exit code when the environment or the SQL file is invalid."""
    try:
        bq.check_environment()
        return parse_file()
    except bq.BqEnvironmentError as exc:
        print(exc, file=sys.stderr)
        return 2
    except DdlError as exc:
        print(exc, file=sys.stderr)
        return 1


def _print_metadata(diffs: list) -> None:
    if diffs:
        print("Diferencias entre BigQuery y la DDL:")
        print(format_table(diffs))


def _run_statements(statements) -> int:
    """Dry run, then execution, of each statement. Stops at the first failure."""
    total = len(statements)
    for i, statement in enumerate(statements, start=1):
        label = f"[{i}/{total}] {_LABELS[statement.kind]} {statement.target}"
        dry = bq.execute(bq.dry_run_query(statement.text))
        if not dry.ok:
            print(f"{label}: el dry run falló y la sentencia no se ejecuta.\n{dry.output}")
            return 1
        estimate = bq.estimated_bytes(dry.output)
        done = bq.execute(bq.run_query(statement.text))
        if not done.ok:
            print(f"{label}: la ejecución falló.\n{done.output}")
            return 1
        shown = "?" if estimate is None else estimate
        print(f"{label}: dry run OK ({shown} bytes estimados), ejecutada")
    return 0


def run_schema() -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    code = _run_statements(
        [s for s in ddl.statements if s.kind in ("create_schema", "create_table")]
    )
    if code:
        return code
    diffs = metadata.verify(ddl.dataset, ddl.tables)
    _print_metadata(diffs)
    print(f"Metadatos: {len(diffs)} diferencias con la DDL")
    return 1 if diffs else 0


def _run_all_checks(
    ddl: Ddl, expectations: dict[str, Parameter], view_mode: str = "required"
) -> int:
    """Metadata and SQL checks. With view_mode "if_exists" a missing view is left out."""
    try:
        include_view = view_mode == "required" or (
            ddl.view is not None and metadata.object_exists(ddl.view.ref)
        )
    except metadata.MetadataError as exc:
        print(exc)
        return 1
    diffs = metadata.verify(ddl.dataset, ddl.tables, ddl.view if include_view else None)
    _print_metadata(diffs)
    if metadata.missing_objects(diffs):
        return 1
    passed, total, _ = checks.run_sql_checks(expectations, include_view=include_view)
    print(f"Chequeos: {passed} de {total} en 0 filas. Metadatos: {len(diffs)} diferencias.")
    return 0 if passed == total and not diffs else 1


def run_checks() -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    return _run_all_checks(ddl, load_expectations())


def run_view() -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    if ddl.view is None:
        print("Falta la sentencia CREATE OR REPLACE VIEW en sql/farma_analytics.sql.")
        return 1
    diffs = metadata.verify(ddl.dataset, ddl.tables)
    if diffs:
        _print_metadata(diffs)
        print("La vista no se despliega hasta que el esquema publicado coincida con la DDL.")
        return 1
    code = _run_statements([s for s in ddl.statements if s.kind == "create_view"])
    if code:
        return code
    return _run_all_checks(ddl, load_expectations())


def run_load(
    repo_root: Path = bq.REPO_ROOT, data_dir: Path | None = None, manifest_path: Path | None = None
) -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    data_dir = Path(data_dir or repo_root / "data")
    manifest_path = Path(manifest_path or MANIFEST_PATH)

    ok_lines, csv_diffs = verify_csv(manifest_path, data_dir)
    for line in ok_lines:
        print(line)
    if csv_diffs:
        for line in csv_diffs:
            print(f"DIFIERE {line}")
        print("Los CSV no coinciden con el manifiesto: ejecuta 'make data'.")
        return 1

    diffs = metadata.verify(ddl.dataset, ddl.tables)
    if diffs:
        _print_metadata(diffs)
        print("La carga no empieza hasta que el esquema publicado coincida con la DDL.")
        return 1

    with tempfile.TemporaryDirectory(prefix="farma-schemas-") as tmp:
        schemas = write_load_schemas(ddl.tables, Path(tmp))
        for table in ddl.tables:
            result = bq.execute(
                bq.load_csv(table.ref, data_dir / f"{table.name}.csv", schemas[table.name])
            )
            if not result.ok:
                print(f"Falló la carga de {table.ref}; la tabla conserva su contenido anterior.")
                print(result.output)
                return 1
            print(f"Cargada {table.ref}")

    code = _run_all_checks(ddl, load_expectations(manifest_path=manifest_path), "if_exists")
    if code:
        return code
    return checks.run_fingerprint()


def run_negative_checks_command() -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    relations = [*ddl.tables, *([ddl.view] if ddl.view is not None else [])]
    return checks.run_negative_checks(load_expectations(), relations)


def run_queries() -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    statements = [s for s in ddl.statements if s.kind == "query"]
    if len(statements) != len(queries.QUERY_IDS):
        print(
            f"sql/farma_analytics.sql debe tener 4 consultas analíticas y tiene {len(statements)}."
        )
        return 1
    try:
        exists = metadata.object_exists(checks.VIEW_REF)
    except metadata.MetadataError as exc:
        print(exc)
        return 1
    if not exists:
        print(f"Falta {checks.VIEW_REF}: ejecuta 'make bq-vista'")
        return 1
    totals = queries.view_totals()
    if isinstance(totals, str):
        print(totals)
        return 1
    results = queries.run_section(statements)
    if isinstance(results, str):
        print(results)
        return 1
    for result in results:
        print(queries.format_result(result))
        print()
    diffs = queries.cross_figures({r.id: r.rows for r in results}, totals)
    if diffs:
        print(format_table(diffs))
        print(f"Cifras cruzadas: {len(diffs)} diferencias.")
        return 1
    print("Cifras cruzadas: 5 de 5 cuadran.")
    return 0
