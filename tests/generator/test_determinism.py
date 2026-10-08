"""Determinism of the generator (FR-006, FR-011, SC-001)."""

from __future__ import annotations

import hashlib
import socket
from pathlib import Path

import pytest

OUTPUTS = ("CLUE_CAT.csv", "COMPRAS.csv", "CUADRO_BASICO.csv", "manifest.json")


def _hashes(directory: Path, names=OUTPUTS) -> dict[str, str]:
    return {n: hashlib.sha256((directory / n).read_bytes()).hexdigest() for n in names}


def test_same_config_same_bytes(run_gen, small_config, tmp_path):
    for name in ("a", "b"):
        proc = run_gen("generate", "--config", str(small_config), "--out", str(tmp_path / name))
        assert proc.returncode == 0, proc.stderr
    assert _hashes(tmp_path / "a") == _hashes(tmp_path / "b")


def test_other_seed_changes_files(run_gen, small_config, tmp_path):
    text = small_config.read_text(encoding="utf-8")
    other = tmp_path / "other.toml"
    other.write_text(
        text.replace('seed = "0xa3b8cf58a2876743564f94c36db190e0"', 'seed = "0x1234abcd"'),
        encoding="utf-8",
    )
    csvs = OUTPUTS[:3]
    assert (
        run_gen("generate", "--config", str(small_config), "--out", str(tmp_path / "a")).returncode
        == 0
    )
    assert run_gen("generate", "--config", str(other), "--out", str(tmp_path / "b")).returncode == 0
    first, second = _hashes(tmp_path / "a", csvs), _hashes(tmp_path / "b", csvs)
    assert all(first[n] != second[n] for n in csvs)


def test_independent_of_timezone_and_locale(run_gen, small_config, tmp_path):
    envs = {"a": {"TZ": "UTC", "LC_ALL": "C"}, "b": {"TZ": "Asia/Tokyo", "LC_ALL": "es_MX.UTF-8"}}
    for name, env in envs.items():
        proc = run_gen(
            "generate", "--config", str(small_config), "--out", str(tmp_path / name), env=env
        )
        assert proc.returncode == 0, proc.stderr
    assert _hashes(tmp_path / "a") == _hashes(tmp_path / "b")


def test_runs_without_network(monkeypatch, small_config, tmp_path):
    from generator.pipeline import generate

    def _blocked(*args, **kwargs):
        raise OSError("network disabled in this test")

    monkeypatch.setattr(socket, "socket", _blocked)
    manifest = generate(small_config, tmp_path / "out")
    assert [f["name"] for f in manifest["files"]] == list(OUTPUTS[:3])


@pytest.mark.parametrize("name", OUTPUTS[:3])
def test_output_has_rows(run_gen, small_config, tmp_path, name):
    proc = run_gen("generate", "--config", str(small_config), "--out", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / name).read_bytes().count(b"\n") > 1
