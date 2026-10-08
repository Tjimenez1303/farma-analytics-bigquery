"""make bq-vista: the view is created after its dry run, then every check runs."""

import json

from warehouse import commands
from warehouse.checks import check_files

VIEW_REF = "farma_analytics.v_compras_farma_completa"


def _queries(fake):
    return [c for c in fake.calls if "query" in c.argv]


def test_deploys_only_the_view_and_runs_every_check(warehouse_env, fake_bq, published, capsys):
    fake_bq.answer_show(published)
    assert commands.run_view() == 0
    queries = _queries(fake_bq)
    dry, run = queries[0], queries[1]
    assert "--dry_run" in dry.argv and "--dry_run" not in run.argv
    assert dry.stdin == run.stdin
    assert dry.stdin.startswith(f"CREATE OR REPLACE VIEW {VIEW_REF}")
    assert any(a.startswith("--label=") for a in run.argv)
    assert len(queries) == 2 + 2 * len(check_files())
    for command in queries:
        assert "CREATE SCHEMA" not in command.stdin
        assert "CREATE TABLE" not in command.stdin
        assert "LIMIT 5" not in command.stdin
    out = capsys.readouterr().out
    assert f"[1/1] CREATE OR REPLACE VIEW {VIEW_REF}: dry run OK" in out
    assert "Chequeos: 7 de 7 en 0 filas. Metadatos: 0 diferencias." in out


def test_missing_table_stops_before_the_dry_run(warehouse_env, fake_bq, published, capsys):
    fake_bq.missing("farma_analytics.CLUE_CAT")
    fake_bq.answer_show(published)
    assert commands.run_view() == 1
    assert _queries(fake_bq) == []
    assert "ejecuta 'make bq-schema'" in capsys.readouterr().out


def test_failed_dry_run_does_not_execute(warehouse_env, fake_bq, published, capsys):
    fake_bq.answer_show(published)
    fake_bq.when(fake_bq.dry_run("CREATE OR REPLACE VIEW"), 1, stderr="Syntax error")
    assert commands.run_view() == 1
    assert not any(fake_bq.query_run("CREATE OR REPLACE VIEW")(c) for c in fake_bq.calls)
    assert "Syntax error" in capsys.readouterr().out


def test_failed_check_after_deploying_returns_one(warehouse_env, fake_bq, published, capsys):
    fake_bq.answer_show(published)
    row = {
        "CHEQUEO": "reconciliacion_vista",
        "OBJETO": "v_compras_farma_completa",
        "DETALLE": "ENTIDAD_ISO nulos",
        "ESPERADO": "0",
        "OBTENIDO": "3",
    }
    fake_bq.when(fake_bq.query_run("'reconciliacion_vista' AS CHEQUEO"), stdout=json.dumps([row]))
    assert commands.run_view() == 1
    assert "Chequeos: 6 de 7 en 0 filas." in capsys.readouterr().out
