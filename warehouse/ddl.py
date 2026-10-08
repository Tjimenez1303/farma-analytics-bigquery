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

# Types of the view columns that are expressions, which the DDL cannot give.
DERIVED_TYPES = {"ANIO": "INT64", "MES": "DATE", "ENTIDAD_ISO": "STRING"}

_ESCAPES = {"\\\\": "\\", "\\'": "'", '\\"': '"', "\\n": "\n", "\\t": "\t"}
_ESCAPE = re.compile(r"\\[\\'\"nt]")
_COMMENT_OR_STRING = re.compile(
    r"--[^\n]*|/\*.*?\*/|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", re.DOTALL
)


class DdlError(Exception):
    """The SQL file cannot be parsed or lacks the expected statements."""


@dataclass(frozen=True)
class Statement:
    kind: str  # create_schema, create_table, create_view, query or other
    text: str  # statement without the terminating semicolon
    line: int
    target: str  # dataset or table reference, empty for other statements


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
class ViewSpec:
    dataset: str
    name: str
    description: str
    query: str
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
    view: ViewSpec | None = None


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
    """A string literal, or CONCAT of string literals to keep long texts under 100 columns."""
    value = options.get(name)
    if value is None:
        return ""
    if value.type != "function":
        return unquote(value.raw)
    leaves = [s for s in value.get_raw_segments() if s.is_code]
    literals = [s for s in leaves if s.is_type("quoted_literal")]
    others = [s.raw for s in leaves if not s.is_type("quoted_literal")]
    if others[:2] != ["CONCAT", "("] or any(raw not in {",", ")"} for raw in others[2:]):
        raise DdlError(f"{name} debe ser una cadena o CONCAT de cadenas: {value.raw}")
    return "".join(unquote(s.raw) for s in literals)


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


def output_name(element) -> tuple[str, object | None]:
    """Output name of a SELECT element and its column reference, if it is a bare column."""
    parts = [s for s in _code(element.segments)]
    alias = next((s for s in parts if s.type == "alias_expression"), None)
    reference = parts[0] if parts[0].type == "column_reference" else None
    if alias is not None:
        name = next(s for s in _code(alias.segments) if s.type == "identifier").raw
    elif reference is not None:
        name = reference.raw.rpartition(".")[2]
    else:
        name = ""
    return name, reference


def output_columns(sql: str) -> list[str]:
    """Output column names of a query, in the order of its final SELECT."""
    tree = _parse(sql, "<consulta>")
    node = next(tree.recursive_crawl("statement", recurse_into=False)).segments[0]
    while node.type != "select_statement":
        node = [s for s in _code(node.segments) if s.type in (*_QUERY_TYPES, "bracketed")][-1]
    clause = next(node.recursive_crawl("select_clause"))
    return [output_name(e)[0] for e in clause.segments if e.type == "select_clause_element"]


def _aliases(select) -> dict[str, str]:
    """Table alias -> table reference of the FROM and JOIN clauses."""
    aliases: dict[str, str] = {}
    for element in select.recursive_crawl("from_expression_element"):
        ref = next(element.recursive_crawl("table_reference")).raw
        alias = next(element.recursive_crawl("alias_expression"), None)
        name = ref if alias is None else next(alias.recursive_crawl("identifier")).raw
        aliases[name] = ref
    return aliases


def _view(body, tables: list[TableSpec], source: str) -> ViewSpec:
    ref = next(body.recursive_crawl("table_reference")).raw
    dataset_name, _, view_name = ref.rpartition(".")
    bracketed = _child(body, "bracketed")
    listed = (
        []
        if bracketed is None
        else [s for s in bracketed.segments if s.type == "column_definition"]
    )
    select = next(s for s in _code(body.segments) if s.type in _QUERY_TYPES)
    clause = next(select.recursive_crawl("select_clause"))
    elements = [s for s in clause.segments if s.type == "select_clause_element"]
    if len(listed) != len(elements):
        raise DdlError(
            f"{source}: la vista {ref} lista {len(listed)} columnas y su SELECT devuelve "
            f"{len(elements)}"
        )
    by_ref = {t.ref: t for t in tables}
    aliases = _aliases(select)
    columns: list[ColumnSpec] = []
    for position, (definition, element) in enumerate(zip(listed, elements, strict=True), 1):
        parts = {s.type: s for s in _code(definition.segments)}
        name = parts["identifier"].raw
        output, reference = output_name(element)
        if output != name:
            raise DdlError(
                f"{source}: en la vista {ref}, la posición {position} de la lista es {name} "
                f"y el SELECT devuelve {output or 'una expresión sin alias'}"
            )
        if reference is not None:
            alias, _, column = reference.raw.rpartition(".")
            table = by_ref[aliases[alias]]
            col_type = next(c.type for c in table.columns if c.name == column)
        elif name in DERIVED_TYPES:
            col_type = DERIVED_TYPES[name]
        else:
            raise DdlError(f"{source}: la columna calculada {name} no tiene tipo en DERIVED_TYPES")
        description = _string_option(_options(parts.get("options_segment")), "description")
        columns.append(ColumnSpec(name, col_type, "NULLABLE", description))
    return ViewSpec(
        dataset=dataset_name,
        name=view_name,
        description=_string_option(_options(_child(body, "options_segment")), "description"),
        query=select.raw,
        columns=tuple(columns),
    )


_QUERY_TYPES = ("select_statement", "with_compound_statement", "set_expression")


def parse_sql(sql: str, source: str = "<sql>") -> Ddl:
    """Statements in order plus the dataset and table specs of the DDL."""
    tree = _parse(sql, source)
    statements: list[Statement] = []
    dataset: DatasetSpec | None = None
    tables: list[TableSpec] = []
    view: ViewSpec | None = None
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
        elif body.type == "create_view_statement":
            view = _view(body, tables, source)
            statements.append(Statement("create_view", statement.raw, line, view.ref))
        elif body.type in _QUERY_TYPES:
            statements.append(Statement("query", statement.raw, line, ""))
        else:
            statements.append(Statement("other", statement.raw, line, ""))
    if dataset is None:
        raise DdlError(f"{source}: falta la sentencia CREATE SCHEMA")
    return Ddl(tuple(statements), dataset, tuple(tables), view)


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
