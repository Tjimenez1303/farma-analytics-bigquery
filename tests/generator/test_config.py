"""Configuration validation and safe writes (FR-010, contracts/config.md)."""

from __future__ import annotations

from pathlib import Path

import pytest


def _variant(small_config: Path, tmp_path: Path, old: str, new: str) -> Path:
    text = small_config.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    path = tmp_path / "variant.toml"
    path.write_text(text.replace(old, new), encoding="utf-8")
    return path


def test_default_config_loads(default_config):
    from generator.config import load_config
    from generator.reference import load_reference

    config = load_config(default_config, load_reference())
    assert config.volumen.lineas_compra == 300000


def test_invalid_orphan_rate_keeps_previous_output(run_gen, small_config, tmp_path):
    out = tmp_path / "data"
    assert run_gen("generate", "--config", str(small_config), "--out", str(out)).returncode == 0
    before = (out / "manifest.json").read_bytes()
    bad = _variant(small_config, tmp_path, "orphan_rate = 0.005", "orphan_rate = -0.1")
    proc = run_gen("generate", "--config", str(bad), "--out", str(out))
    assert proc.returncode == 2
    assert "huerfanos.orphan_rate" in proc.stderr and "[0, 0.05]" in proc.stderr
    assert (out / "manifest.json").read_bytes() == before


INVALID = [
    ("fin = 2025-12-31", "fin = 2024-12-31", "periodo"),
    (
        "factores_mes = [1.25, 1.15, 1.10, 1.00, 0.95, 0.95, 0.90, 0.95, 1.00, 0.95, 0.90, 0.90]",
        "factores_mes = [1.25, 1.15, 1.10, 1.00, 0.95, 0.95, 0.90, 0.95, 1.00, 0.95, 0.90]",
        "estacionalidad.factores_mes",
    ),
    (
        '"IMSS" = 0.42, "IMSS-Bienestar"',
        '"IMSS" = 0.50, "IMSS-Bienestar"',
        "concentracion.participacion_institucion",
    ),
    (
        'prob_referencia = { "PEMEX"',
        'prob_referencia = { "CRUZ ROJA" = 0.1, "PEMEX"',
        "patrones.p3.prob_referencia",
    ),
    (
        'molecula_ejemplo = "Clopidogrel"',
        'molecula_ejemplo = "Atorvastatina"',
        "patrones.p3.molecula_ejemplo",
    ),
    (
        'moleculas = ["Atorvastatina", "Insulina glargina"]',
        'moleculas = ["Atorvastatina", "Metformina"]',
        "patrones.p5.moleculas",
    ),
    (
        "genericos_por_molecula = [1, 4]",
        "genericos_por_molecula = [1, 40]",
        "volumen.genericos_por_molecula",
    ),
    (
        "solo_dias_laborables = true",
        "solo_dias_laborables = true\nzona_horaria = 'UTC'",
        "periodo.zona_horaria",
    ),
]


@pytest.mark.parametrize(("old", "new", "path"), INVALID, ids=[case[2] for case in INVALID])
def test_invalid_values_exit_2(run_gen, small_config, tmp_path, old, new, path):
    bad = _variant(small_config, tmp_path, old, new)
    proc = run_gen("generate", "--config", str(bad), "--out", str(tmp_path / "out"))
    assert proc.returncode == 2
    assert path in proc.stderr
    assert not (tmp_path / "out").exists()


def test_missing_output_dir_is_created(run_gen, small_config, tmp_path):
    out = tmp_path / "new" / "data"
    proc = run_gen("generate", "--config", str(small_config), "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    assert (out / "manifest.json").exists()


def test_failure_inside_staging_keeps_output(monkeypatch, small_config, tmp_path):
    from generator import pipeline

    out = tmp_path / "data"
    pipeline.generate(small_config, out)
    before = {p.name: p.read_bytes() for p in out.iterdir()}

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(pipeline, "write_csv", _boom)
    with pytest.raises(RuntimeError):
        pipeline.generate(small_config, out)
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before
    assert not list(out.glob(".tmp-*"))
