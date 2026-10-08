"""make bq-schema: dry run before each statement, then metadata verification."""

from warehouse import commands


def test_runs_each_statement_after_its_dry_run(warehouse_env, fake_bq, published, capsys):
    fake_bq.answer_show(published)
    assert commands.run_schema() == 0
    queries = [c for c in fake_bq.calls if "query" in c.argv]
    assert len(queries) == 8
    for dry, run in zip(queries[::2], queries[1::2], strict=True):
        assert "--dry_run" in dry.argv
        assert "--dry_run" not in run.argv
        assert dry.stdin == run.stdin
    out = capsys.readouterr().out
    assert "[1/4] CREATE SCHEMA farma_analytics: dry run OK" in out
    assert "Metadatos: 0 diferencias con la DDL" in out


def test_failed_dry_run_stops_before_executing(warehouse_env, fake_bq, published, capsys):
    fake_bq.when(fake_bq.dry_run("farma_analytics.CLUE_CAT"), 1, stderr="Syntax error")
    fake_bq.answer_show(published)
    assert commands.run_schema() == 1
    runs = [c.stdin for c in fake_bq.calls if fake_bq.query_run()(c)]
    assert len(runs) == 2
    assert not any("CLUE_CAT" in sql or "CUADRO_BASICO (" in sql for sql in runs)
    assert not fake_bq.with_verb("show")
    out = capsys.readouterr().out
    assert "[3/4]" in out and "Syntax error" in out


def test_failed_execution_returns_one(warehouse_env, fake_bq, published):
    fake_bq.when(fake_bq.query_run("CREATE SCHEMA"), 1, stderr="Access Denied")
    assert commands.run_schema() == 1


def test_metadata_difference_returns_one(warehouse_env, fake_bq, published, capsys):
    published["farma_analytics"]["location"] = "EU"
    fake_bq.answer_show(published)
    assert commands.run_schema() == 1
    assert "Metadatos: 1 diferencias con la DDL" in capsys.readouterr().out


def test_invalid_environment_returns_two(warehouse_env, fake_bq, monkeypatch):
    monkeypatch.delenv("PROJECT_ID")
    assert commands.run_schema() == 2
    assert fake_bq.calls == []
