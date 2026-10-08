"""bq command construction and environment checks (no bq is executed)."""

from pathlib import Path

import pytest

from warehouse import bq

FIXED_BY_BIGQUERYRC = ("--location", "--use_legacy_sql", "--maximum_bytes_billed")


def test_dry_run_query_sends_sql_on_stdin(warehouse_env):
    command = bq.dry_run_query("-- comment\nSELECT 1", ["--parameter=x:INT64:1"])
    assert command.argv == (
        "bq",
        "--project_id=proyecto-prueba",
        "query",
        "--dry_run",
        "--parameter=x:INT64:1",
    )
    assert command.stdin == "-- comment\nSELECT 1"


def test_run_query_has_labels_json_and_max_rows(warehouse_env):
    command = bq.run_query("SELECT 1", ["--parameter=x:INT64:1"], as_json=True, max_rows=1000)
    assert command.argv == (
        "bq",
        "--project_id=proyecto-prueba",
        "--format=json",
        "query",
        "--label=project:farma-analytics",
        "--label=env:dev",
        "--max_rows=1000",
        "--parameter=x:INT64:1",
    )
    assert command.stdin == "SELECT 1"


def test_run_query_without_options(warehouse_env):
    command = bq.run_query("SELECT 1")
    assert "--format=json" not in command.argv
    assert not any(a.startswith("--max_rows") for a in command.argv)


def test_load_csv_flags(warehouse_env):
    command = bq.load_csv("farma_analytics.COMPRAS", Path("d/COMPRAS.csv"), Path("s/COMPRAS.json"))
    assert command.argv == (
        "bq",
        "--project_id=proyecto-prueba",
        "load",
        "--replace",
        "--source_format=CSV",
        "--skip_leading_rows=1",
        "--autodetect=false",
        "--max_bad_records=0",
        "--encoding=UTF-8",
        "farma_analytics.COMPRAS",
        "d/COMPRAS.csv",
        "s/COMPRAS.json",
    )
    assert command.stdin is None


def test_show(warehouse_env):
    assert bq.show("farma_analytics").argv == (
        "bq",
        "--project_id=proyecto-prueba",
        "--format=json",
        "show",
        "farma_analytics",
    )


def test_no_command_repeats_bigqueryrc_flags_and_labels_only_on_runs(warehouse_env):
    commands = [
        bq.dry_run_query("SELECT 1"),
        bq.run_query("SELECT 1", as_json=True, max_rows=10),
        bq.load_csv("farma_analytics.COMPRAS", Path("a.csv"), Path("a.json")),
        bq.show("farma_analytics"),
    ]
    for command in commands:
        assert not any(a.startswith(FIXED_BY_BIGQUERYRC) for a in command.argv), command
        has_label = any(a.startswith("--label=") for a in command.argv)
        is_run = "query" in command.argv and "--dry_run" not in command.argv
        assert has_label == is_run, command


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (
            (
                "Query successfully validated. Assuming the tables are not modified, "
                "running this query will process 1234 bytes of data."
            ),
            1234,
        ),
        ("Query successfully validated.", None),
    ],
)
def test_estimated_bytes(output, expected):
    assert bq.estimated_bytes(output) == expected


def test_environment_ok(warehouse_env):
    bq.check_environment()


def test_environment_rejects_other_bigqueryrc(warehouse_env, monkeypatch, tmp_path):
    other = tmp_path / ".bigqueryrc"
    other.write_text("--location=EU\n")
    monkeypatch.setenv("BIGQUERYRC", str(other))
    with pytest.raises(bq.BqEnvironmentError, match="BIGQUERYRC"):
        bq.check_environment()


def test_environment_requires_project(warehouse_env, monkeypatch):
    monkeypatch.delenv("PROJECT_ID")
    with pytest.raises(bq.BqEnvironmentError, match="PROJECT_ID"):
        bq.check_environment()


def test_environment_requires_labels(warehouse_env, monkeypatch):
    monkeypatch.setenv("BQ_JOB_LABELS", "project:farma-analytics")
    with pytest.raises(bq.BqEnvironmentError, match="BQ_JOB_LABELS"):
        bq.check_environment()


def test_environment_requires_bq_on_path(warehouse_env, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(bq.BqEnvironmentError, match="bq"):
        bq.check_environment()
