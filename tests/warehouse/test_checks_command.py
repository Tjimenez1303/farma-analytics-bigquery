"""make bq-checks: metadata first, then each check after its dry run."""

import json

from warehouse import commands
from warehouse.checks import MAX_ROWS, check_files

ROW = {
    "CHEQUEO": "nulos",
    "OBJETO": "COMPRAS.CLUE",
    "DETALLE": "nulos",
    "ESPERADO": "0",
    "OBTENIDO": "3",
}


def _check_queries(fake):
    return [c for c in fake.calls if "query" in c.argv]


def test_all_checks_pass(warehouse_env, fake_bq, published, capsys):
    fake_bq.answer_show(published)
    assert commands.run_checks() == 0
    assert "show" in fake_bq.calls[0].argv
    queries = _check_queries(fake_bq)
    assert len(queries) == 2 * len(check_files())
    for dry, run, path in zip(queries[::2], queries[1::2], check_files(), strict=True):
        sql = path.read_text(encoding="utf-8")
        assert dry.stdin == run.stdin == sql
        assert "--dry_run" in dry.argv
        assert "--format=json" in run.argv
        assert f"--max_rows={MAX_ROWS}" in run.argv
        assert [a for a in dry.argv if a.startswith("--parameter")] == [
            a for a in run.argv if a.startswith("--parameter")
        ]
    out = capsys.readouterr().out
    assert "Chequeos: 7 de 7 en 0 filas. Metadatos: 0 diferencias." in out


def test_each_check_gets_only_its_parameters(warehouse_env, fake_bq, published):
    fake_bq.answer_show(published)
    commands.run_checks()
    runs = [c for c in _check_queries(fake_bq) if "--dry_run" not in c.argv]
    unicidad = runs[1]
    assert not any(a.startswith("--parameter") for a in unicidad.argv)
    dominios = runs[3]
    assert sorted(a for a in dominios.argv if a.startswith("--parameter")) == [
        "--parameter=fecha_fin:DATE:2025-12-31",
        "--parameter=fecha_inicio:DATE:2024-01-01",
    ]


def test_failing_check_reports_rows_and_continues(warehouse_env, fake_bq, published, capsys):
    fake_bq.answer_show(published)
    fake_bq.when(fake_bq.query_run("'nulos' AS CHEQUEO"), stdout=json.dumps([ROW]))
    assert commands.run_checks() == 1
    assert len(_check_queries(fake_bq)) == 2 * len(check_files())
    out = capsys.readouterr().out
    assert "FALLO nulos: 1 filas" in out
    assert "COMPRAS.CLUE" in out
    assert "Chequeos: 6 de 7 en 0 filas." in out


def test_truncated_output_is_reported(warehouse_env, fake_bq, published, capsys):
    fake_bq.answer_show(published)
    fake_bq.when(fake_bq.query_run("'nulos' AS CHEQUEO"), stdout=json.dumps([ROW] * MAX_ROWS))
    assert commands.run_checks() == 1
    assert f"{MAX_ROWS} o más filas" in capsys.readouterr().out


def test_failed_dry_run_skips_that_check(warehouse_env, fake_bq, published, capsys):
    fake_bq.answer_show(published)
    fake_bq.when(fake_bq.dry_run("'dominios' AS CHEQUEO"), 1, stderr="Unrecognized name")
    assert commands.run_checks() == 1
    assert not any(fake_bq.query_run("'dominios' AS CHEQUEO")(c) for c in fake_bq.calls)
    assert "el dry run falló" in capsys.readouterr().out


def test_metadata_difference_fails(warehouse_env, fake_bq, published, capsys):
    published["farma_analytics.COMPRAS"]["description"] = "otra"
    fake_bq.answer_show(published)
    assert commands.run_checks() == 1
    assert "Metadatos: 1 diferencias." in capsys.readouterr().out


def test_missing_view_fails(warehouse_env, fake_bq, published, capsys):
    fake_bq.missing("farma_analytics.v_compras_farma_completa")
    fake_bq.answer_show(published)
    assert commands.run_checks() == 1
    assert _check_queries(fake_bq) == []
    out = capsys.readouterr().out
    assert "Falta farma_analytics.v_compras_farma_completa: ejecuta 'make bq-vista'" in out


def test_missing_dataset_skips_sql_checks(warehouse_env, fake_bq, capsys):
    fake_bq.when(fake_bq.show("farma_analytics"), 2, stdout="Not found: Dataset")
    assert commands.run_checks() == 1
    assert _check_queries(fake_bq) == []
    assert "make bq-schema" in capsys.readouterr().out
