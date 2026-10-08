"""Analysis of sql/farma_analytics.sql with the SQLFluff parser (bigquery dialect)."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from sqlfluff.core import Linter

from warehouse.bq import REPO_ROOT

DDL_PATH = REPO_ROOT / "sql" / "farma_analytics.sql"

_ESCAPES = {"\\\\": "\\", "\\'": "'", '\\"': '"', "\\n": "\n", "\\t": "\t"}
_ESCAPE = re.compile(r"\\[\\'\"nt]")
_COMMENT_OR_STRING = re.compile(
    r"--[^\n]*|/\*.*?\*/|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", re.DOTALL
)


class DdlError(Exception):
    """The SQL file cannot be parsed or lacks the expected statements."""


@dataclass(frozen=True)
class Statement:
    kind: str  # create_schema, create_table or other
    text: str  # statement without the terminating semicolon
    line: int
    target: str  # dataset or table reference; empty for other statements


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    type: str
    mode: str
    description: str


@dataclass(frozen=True)
class TableSpec:
    dataset: str
    name: str
    description: str
    columns: tuple[ColumnSpec, ...]

    @property
    def ref(self) -> str:
        return f"{self.dataset}.{self.name}"


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    location: str
    description: str
    labels: dict[str, str]


@dataclass(frozen=True)
class Ddl:
    statements: tuple[Statement, ...]
    dataset: DatasetSpec
    tables: tuple[TableSpec, ...]


def unquote(literal: str) -> str:
    """Value of a GoogleSQL single- or double-quoted string literal."""
    if len(literal) < 2 or literal[0] not in "'\"" or literal[-1] != literal[0]:
        raise DdlError(f"No es una cadena entre comillas: {literal}")
    return _ESCAPE.sub(lambda m: _ESCAPES[m.group(0)], literal[1:-1])


def strip_comments_and_strings(sql: str) -> str:
    """SQL with comments and string literals blanked, keeping line breaks."""
    return _COMMENT_OR_STRING.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), sql)


def _parse(sql: str, source: str):
    parsed = Linter(dialect="bigquery").parse_string(sql)
    if parsed.violations or any(True for _ in parsed.tree.recursive_crawl("unparsable")):
        details = "; ".join(v.desc() for v in parsed.violations) or "sección no analizable"
        raise DdlError(f"{source}: SQL no válido para el dialecto bigquery ({details})")
    return parsed.tree


def _code(segments: Iterable) -> Iterator:
    return (s for s in segments if s.is_code)


def _options(segment) -> dict[str, object]:
    """name -> value segment of an OPTIONS (...) list."""
    if segment is None:
        return {}
    bracketed = next(s for s in segment.segments if s.type == "bracketed")
    values: dict[str, object] = {}
    items = list(_code(bracketed.segments))
    for i, item in enumerate(items):
        if item.is_type("parameter"):
            values[item.raw.lower()] = items[i + 2]  # parameter, '=', value
    return values


def _string_option(options: dict[str, object], name: str) -> str:
    value = options.get(name)
    return unquote(value.raw) if value is not None else ""


def _labels(options: dict[str, object]) -> dict[str, str]:
    value = options.get("labels")
    if value is None:
        return {}
    literals = [unquote(s.raw) for s in value.recursive_crawl("quoted_literal")]
    return dict(zip(literals[::2], literals[1::2], strict=True))


def _child(segment, kind: str):
    return next((s for s in segment.segments if s.type == kind), None)


def _column(definition) -> ColumnSpec:
    parts = {s.type: s for s in _code(definition.segments)}
    constraint = parts.get("column_constraint_segment")
    not_null = constraint is not None and constraint.raw.upper().split() == ["NOT", "NULL"]
    return ColumnSpec(
        name=parts["identifier"].raw,
        type=parts["data_type"].raw.upper(),
        mode="REQUIRED" if not_null else "NULLABLE",
        description=_string_option(_options(parts.get("options_segment")), "description"),
    )


def parse_sql(sql: str, source: str = "<sql>") -> Ddl:
    """Statements in order plus the dataset and table specs of the DDL."""
    tree = _parse(sql, source)
    statements: list[Statement] = []
    dataset: DatasetSpec | None = None
    tables: list[TableSpec] = []
    for statement in tree.recursive_crawl("statement", recurse_into=False):
        body = statement.segments[0]
        line = statement.pos_marker.line_no
        if body.type == "create_schema_statement":
            name = next(body.recursive_crawl("table_reference")).raw
            options = _options(_child(body, "options_segment"))
            dataset = DatasetSpec(
                name=name,
                location=_string_option(options, "location"),
                description=_string_option(options, "description"),
                labels=_labels(options),
            )
            statements.append(Statement("create_schema", statement.raw, line, name))
        elif body.type == "create_table_statement":
            ref = next(body.recursive_crawl("table_reference")).raw
            dataset_name, _, table_name = ref.rpartition(".")
            options = _options(_child(body, "options_segment"))
            columns = tuple(_column(d) for d in body.recursive_crawl("column_definition"))
            tables.append(
                TableSpec(
                    dataset=dataset_name,
                    name=table_name,
                    description=_string_option(options, "description"),
                    columns=columns,
                )
            )
            statements.append(Statement("create_table", statement.raw, line, ref))
        else:
            statements.append(Statement("other", statement.raw, line, ""))
    if dataset is None:
        raise DdlError(f"{source}: falta la sentencia CREATE SCHEMA")
    return Ddl(tuple(statements), dataset, tuple(tables))


def parse_file(path: Path = DDL_PATH) -> Ddl:
    path = Path(path)
    return parse_sql(path.read_text(encoding="utf-8"), str(path))


def load_schema(table: TableSpec) -> list[dict[str, str]]:
    """bq load JSON schema of a table, derived from its CREATE TABLE."""
    return [
        {"name": c.name, "type": c.type, "mode": c.mode, "description": c.description}
        for c in table.columns
    ]


def write_load_schemas(tables: Iterable[TableSpec], directory: Path) -> dict[str, Path]:
    """One <TABLE>.json schema file per table in directory."""
    paths: dict[str, Path] = {}
    for table in tables:
        path = Path(directory) / f"{table.name}.json"
        path.write_text(
            json.dumps(load_schema(table), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        paths[table.name] = path
    return paths
