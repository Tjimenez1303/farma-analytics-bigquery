"""Manifest format and verification (FR-007, FR-008, contracts/manifest.md)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

CSV_NAMES = ["CLUE_CAT.csv", "COMPRAS.csv", "CUADRO_BASICO.csv"]


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    from generator.pipeline import generate

    out = tmp_path_factory.mktemp("manifest")
    small = Path(__file__).resolve().parent / "fixtures" / "config_small.toml"
    generate(small, out)
    return out


def test_manifest_keys_and_files(generated):
    text = (generated / "manifest.json").read_text(encoding="utf-8")
    assert text.endswith("}\n")
    manifest = json.loads(text)
    assert sorted(manifest) == ["config_sha256", "files", "format_version", "orphans", "versions"]
    assert manifest["format_version"] == 1
    assert [f["name"] for f in manifest["files"]] == CSV_NAMES
    assert sorted(manifest["orphans"]) == ["CLAVE", "CLUE"]
    assert sorted(manifest["versions"]) == ["faker", "numpy", "python"]
    for entry in manifest["files"]:
        data = (generated / entry["name"]).read_bytes()
        assert sorted(entry) == ["bytes", "name", "rows", "sha256"]
        assert entry["sha256"] == hashlib.sha256(data).hexdigest()
        assert entry["bytes"] == len(data)
        assert entry["rows"] == data.count(b"\n") - 1


def test_config_hash(generated):
    manifest = json.loads((generated / "manifest.json").read_text(encoding="utf-8"))
    small = Path(__file__).resolve().parent / "fixtures" / "config_small.toml"
    assert manifest["config_sha256"] == hashlib.sha256(small.read_bytes()).hexdigest()


def test_no_dates_or_absolute_paths(generated):
    text = (generated / "manifest.json").read_text(encoding="utf-8")
    assert not re.search(r"\d{4}-\d{2}-\d{2}", text)
    assert str(generated) not in text


def test_verify_ok_against_own_manifest(run_gen, generated):
    proc = run_gen(
        "verify", "--manifest", str(generated / "manifest.json"), "--data", str(generated)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.count(": OK") == 3


def test_verify_detects_altered_byte(run_gen, generated, tmp_path):
    data = tmp_path / "data"
    shutil.copytree(generated, data)
    compras = data / "COMPRAS.csv"
    raw = bytearray(compras.read_bytes())
    raw[-5] = ord("9") if raw[-5] != ord("9") else ord("8")
    compras.write_bytes(bytes(raw))
    proc = run_gen("verify", "--manifest", str(generated / "manifest.json"), "--data", str(data))
    assert proc.returncode == 1
    assert "DIFIERE COMPRAS.csv" in proc.stdout


def test_verify_detects_missing_file(run_gen, generated, tmp_path):
    data = tmp_path / "data"
    shutil.copytree(generated, data)
    (data / "CLUE_CAT.csv").unlink()
    proc = run_gen("verify", "--manifest", str(generated / "manifest.json"), "--data", str(data))
    assert proc.returncode == 1
    assert "CLUE_CAT.csv: falta el archivo" in proc.stdout
