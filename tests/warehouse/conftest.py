"""Fixtures for the warehouse tests: a fake bq and a valid environment, without GCP."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from warehouse import bq
from warehouse.ddl import Ddl, ViewSpec, parse_file

REPO_ROOT = Path(__file__).resolve().parents[2]
STUB_BIN = REPO_ROOT / "tests" / "fixtures" / "stubs" / "bin"
LABELS = "--label=project:farma-analytics --label=env:dev"

_API_TYPES = {"INT64": "INTEGER"}

Predicate = Callable[[bq.Command], bool]


@dataclass
class FakeBq:
    """Records every bq command and answers with the first matching rule."""

    calls: list[bq.Command] = field(default_factory=list)
    rules: list[tuple[Predicate, bq.BqResult]] = field(default_factory=list)

    def when(self, predicate: Predicate, returncode=0, stdout="", stderr="") -> FakeBq:
        self.rules.append((predicate, bq.BqResult(returncode, stdout, stderr)))
        return self

    def __call__(self, command: bq.Command) -> bq.BqResult:
        self.calls.append(command)
        for predicate, result in self.rules:
            if predicate(command):
                return result
        return bq.BqResult(0, "", "")

    def answer_show(self, metadata: dict[str, dict]) -> FakeBq:
        for ref, body in metadata.items():
            self.when(self.show(ref), stdout=json.dumps(body, ensure_ascii=False))
        return self

    def with_verb(self, verb: str) -> list[bq.Command]:
        return [c for c in self.calls if verb in c.argv]

    def missing(self, ref: str) -> FakeBq:
        """bq show of ref answers Not found, as BigQuery does for a missing view."""
        return self.when(self.show(ref), 2, stdout=f"Not found: Table {ref}")

    @staticmethod
    def show(ref: str) -> Predicate:
        return lambda c: "show" in c.argv and c.argv[-1] == ref

    @staticmethod
    def dry_run(text: str = "") -> Predicate:
        return lambda c: "--dry_run" in c.argv and text in (c.stdin or "")

    @staticmethod
    def query_run(text: str = "") -> Predicate:
        return lambda c: "query" in c.argv and "--dry_run" not in c.argv and text in (c.stdin or "")

    @staticmethod
    def load(table_ref: str) -> Predicate:
        return lambda c: "load" in c.argv and table_ref in c.argv


def _view_metadata(view: ViewSpec) -> dict:
    """bq show JSON of a GoogleSQL view that matches its section 3 definition."""
    fields = [
        {
            "name": column.name,
            "type": _API_TYPES.get(column.type, column.type),
            "description": column.description,
        }
        for column in view.columns
    ]
    return {
        "type": "VIEW",
        "view": {"query": view.query, "useLegacySql": False},
        "description": view.description,
        "schema": {"fields": fields},
    }


@pytest.fixture
def view_metadata() -> Callable[[ViewSpec], dict]:
    return _view_metadata


@pytest.fixture
def ddl() -> Ddl:
    return parse_file()


@pytest.fixture
def published(ddl) -> dict[str, dict]:
    """bq show JSON that matches the DDL exactly, keyed by reference."""
    data = {
        ddl.dataset.name: {
            "location": ddl.dataset.location,
            "description": ddl.dataset.description,
            "labels": dict(ddl.dataset.labels),
        }
    }
    for table in ddl.tables:
        fields = []
        for column in table.columns:
            item = {"name": column.name, "type": _API_TYPES.get(column.type, column.type)}
            if column.mode != "NULLABLE":
                item["mode"] = column.mode
            item["description"] = column.description
            fields.append(item)
        data[table.ref] = {"description": table.description, "schema": {"fields": fields}}
    if ddl.view is not None:
        data[ddl.view.ref] = _view_metadata(ddl.view)
    return data


@pytest.fixture
def fake_bq(monkeypatch) -> FakeBq:
    fake = FakeBq()
    monkeypatch.setattr(bq, "execute", fake)
    return fake


@pytest.fixture
def warehouse_env(monkeypatch):
    """Repository .bigqueryrc, a test project, the Makefile labels and the stub bq on PATH."""
    monkeypatch.setenv("BIGQUERYRC", str(REPO_ROOT / ".bigqueryrc"))
    monkeypatch.setenv("PROJECT_ID", "proyecto-prueba")
    monkeypatch.setenv("BQ_JOB_LABELS", LABELS)
    monkeypatch.setenv("PATH", str(STUB_BIN), prepend=os.pathsep)
