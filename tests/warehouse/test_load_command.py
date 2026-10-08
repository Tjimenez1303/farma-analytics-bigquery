"""make bq-load: CSV verification, metadata, atomic loads, checks and fingerprint."""

import json
from pathlib import Path

import pytest

from generator.manifest import build_manifest, dumps, file_entry
from warehouse import commands

CSV = {
    "COMPRAS": "CLUE,CLAVE,COD_PROVEEDOR,MARCA,FABRICANTE,PIEZAS,IMPORTE,FECHA\n"
    "A,B,P,M,F,1,10.00,2024-01-02\n",
    "CLUE_CAT": "CLUE,ENTIDAD,INSTITUCION,DELEGACION,GRUPO_INSTITUCIONAL,NIVEL_ATENCION,"
    "MUNICIPIO\nA,E,I,D,G,N,M\n",
    "CUADRO_BASICO": "CLAVE,DESCRIPCION,MOLECULA,GRUPO_TERAPEUTICO,PRESENTACION,FABRICANTE\n"
    "B,D,M,G,P,F\n",
}
FINGERPRINT_ROWS = [
    {"TABLA": "COMPRAS", "FILAS": "1", "HUELLA": "42"},
    {"TABLA": "CLUE_CAT", "FILAS": "1", "HUELLA": "7"},
    {"TABLA": "CUADRO_BASICO", "FILAS": "1", "HUELLA": "9"},
]


@pytest.fixture
def data(tmp_path):
    """data/ with three CSV files and the matching expected manifest."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name, text in CSV.items():
        (data_dir / f"{name}.csv").write_text(text, encoding="utf-8")
    files = [file_entry(data_dir / f"{name}.csv") for name in CSV]
    manifest = build_manifest(b"config", files, {"CLAVE": 0, "CLUE": 0})
    (data_dir / "manifest.json").write_text(dumps(manifest), encoding="utf-8")
    expected = tmp_path / "manifest.json"
    expected.write_text(dumps(manifest), encoding="utf-8")
    return data_dir, expected


def _run(data):
    data_dir, manifest = data
    return commands.run_load(data_dir=data_dir, manifest_path=manifest)


def _loads(fake):
    return fake.with_verb("load")


def test_csv_mismatch_stops_before_bq(warehouse_env, fake_bq, data, capsys):
    (data[0] / "COMPRAS.csv").write_text("cambiado\n", encoding="utf-8")
    assert _run(data) == 1
    assert fake_bq.calls == []
    assert "ejecuta 'make data'" in capsys.readouterr().out


def test_missing_csv_stops_before_bq(warehouse_env, fake_bq, data, capsys):
    (data[0] / "CLUE_CAT.csv").unlink()
    assert _run(data) == 1
    assert fake_bq.calls == []
    assert "falta el archivo" in capsys.readouterr().out


def test_missing_table_stops_before_loading(warehouse_env, fake_bq, published, data, capsys):
    fake_bq.when(fake_bq.show("farma_analytics.CLUE_CAT"), 2, stderr="Not found: Table")
    fake_bq.answer_show(published)
    assert _run(data) == 1
    assert _loads(fake_bq) == []
    assert "ejecuta 'make bq-schema'" in capsys.readouterr().out


def test_successful_load(warehouse_env, fake_bq, published, data, capsys):
    fake_bq.answer_show(published)
    fake_bq.when(fake_bq.query_run("AS HUELLA"), stdout=json.dumps(FINGERPRINT_ROWS))
    assert _run(data) == 0

    loads = _loads(fake_bq)
    assert [c.argv[-3] for c in loads] == [
        "farma_analytics.COMPRAS",
        "farma_analytics.CLUE_CAT",
        "farma_analytics.CUADRO_BASICO",
    ]
    for command in loads:
        table = command.argv[-3].split(".")[1]
        assert command.argv[-2] == str(data[0] / f"{table}.csv")
        schema = Path(command.argv[-1])
        assert schema.name == f"{table}.json"
        assert not schema.exists()

    first_load = fake_bq.calls.index(loads[0])
    last_load = fake_bq.calls.index(loads[-1])
    assert any("show" in c.argv for c in fake_bq.calls[:first_load])
    assert any("show" in c.argv for c in fake_bq.calls[last_load:])
    checks = [c for c in fake_bq.calls[last_load:] if "query" in c.argv]
    assert len(checks) == 16  # seven checks and the fingerprint, each with its dry run

    out = capsys.readouterr().out
    assert "Chequeos: 7 de 7 en 0 filas. Metadatos: 0 diferencias." in out
    assert "COMPRAS        1      42" in out


def test_load_without_view_warns_and_passes(warehouse_env, fake_bq, published, data, capsys):
    fake_bq.missing("farma_analytics.v_compras_farma_completa")
    fake_bq.answer_show(published)
    fake_bq.when(fake_bq.query_run("AS HUELLA"), stdout=json.dumps(FINGERPRINT_ROWS))
    assert _run(data) == 0
    queries = [c for c in fake_bq.calls if "query" in c.argv]
    assert not any("CREATE OR REPLACE VIEW" in c.stdin for c in queries)
    assert not any("'reconciliacion_vista' AS CHEQUEO" in c.stdin for c in queries)
    out = capsys.readouterr().out
    assert "La vista no está desplegada: ejecuta 'make bq-vista'." in out
    assert "Chequeos: 6 de 6 en 0 filas. Metadatos: 0 diferencias." in out


def test_failed_load_keeps_previous_content(warehouse_env, fake_bq, published, data, capsys):
    fake_bq.answer_show(published)
    fake_bq.when(fake_bq.load("farma_analytics.CLUE_CAT"), 1, stderr="Error while reading data")
    assert _run(data) == 1
    assert [c.argv[-3] for c in _loads(fake_bq)] == [
        "farma_analytics.COMPRAS",
        "farma_analytics.CLUE_CAT",
    ]
    out = capsys.readouterr().out
    assert "Falló la carga de farma_analytics.CLUE_CAT" in out
    assert "Error while reading data" in out


def test_failed_check_skips_fingerprint(warehouse_env, fake_bq, published, data, capsys):
    fake_bq.answer_show(published)
    row = {
        "CHEQUEO": "unicidad_claves",
        "OBJETO": "CLUE_CAT.CLUE",
        "DETALLE": "A",
        "ESPERADO": "1",
        "OBTENIDO": "2",
    }
    fake_bq.when(fake_bq.query_run("'unicidad_claves' AS CHEQUEO"), stdout=json.dumps([row]))
    assert _run(data) == 1
    assert not any("AS HUELLA" in (c.stdin or "") for c in fake_bq.calls)
    assert "Chequeos: 6 de 7 en 0 filas." in capsys.readouterr().out


def test_view_lookup_error_fails_the_load(warehouse_env, fake_bq, published, data, capsys):
    fake_bq.when(
        fake_bq.show("farma_analytics.v_compras_farma_completa"), 2, stderr="Access Denied"
    )
    fake_bq.answer_show(published)
    assert _run(data) == 1
    assert "Access Denied" in capsys.readouterr().out
