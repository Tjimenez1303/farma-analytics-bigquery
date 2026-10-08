"""Orchestration of the schema, load, checks and checks-negativos commands."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from generator.manifest import verify as verify_csv
from warehouse import bq, checks, metadata
from warehouse.ddl import Ddl, DdlError, parse_file, write_load_schemas
from warehouse.expectations import MANIFEST_PATH, Parameter, load_expectations
from warehouse.results import format_table

_LABELS = {"create_schema": "CREATE SCHEMA", "create_table": "CREATE TABLE"}


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


def run_schema() -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    statements = [s for s in ddl.statements if s.kind in _LABELS]
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
    diffs = metadata.verify(ddl.dataset, ddl.tables)
    _print_metadata(diffs)
    print(f"Metadatos: {len(diffs)} diferencias con la DDL")
    return 1 if diffs else 0


def _run_all_checks(ddl: Ddl, expectations: dict[str, Parameter]) -> int:
    diffs = metadata.verify(ddl.dataset, ddl.tables)
    _print_metadata(diffs)
    if metadata.missing_objects(diffs):
        return 1
    passed, total, _ = checks.run_sql_checks(expectations)
    print(f"Chequeos: {passed} de {total} en 0 filas. Metadatos: {len(diffs)} diferencias.")
    return 0 if passed == total and not diffs else 1


def run_checks() -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    return _run_all_checks(ddl, load_expectations())


def run_load(
    repo_root: Path = bq.REPO_ROOT,
    data_dir: Path | None = None,
    manifest_path: Path | None = None,
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

    code = _run_all_checks(ddl, load_expectations(manifest_path=manifest_path))
    if code:
        return code
    return checks.run_fingerprint()


def run_negative_checks_command() -> int:
    ddl = _environment()
    if isinstance(ddl, int):
        return ddl
    return checks.run_negative_checks(load_expectations(), ddl.tables)
