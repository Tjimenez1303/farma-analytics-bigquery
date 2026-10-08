"""Key uniqueness, completeness and orphans (FR-012 to FR-014, SC-004)."""

from __future__ import annotations

import json
from pathlib import Path

ORPHAN_RATE = 0.005
LINEAS = 300_000
PROPORCION_CLUE = 0.5


def test_catalog_keys_are_unique(full_tables):
    clues = [r["CLUE"] for r in full_tables["CLUE_CAT"]]
    claves = [r["CLAVE"] for r in full_tables["CUADRO_BASICO"]]
    assert len(clues) == len(set(clues))
    assert len(claves) == len(set(claves))


def test_no_empty_fields(full_tables):
    for rows in full_tables.values():
        assert all(v != "" for r in rows for v in r.values())


def test_orphans_exact_and_disjoint(full_dataset, full_tables):
    clues = {r["CLUE"] for r in full_tables["CLUE_CAT"]}
    claves = {r["CLAVE"] for r in full_tables["CUADRO_BASICO"]}
    compras = full_tables["COMPRAS"]
    clue_orphans = [i for i, r in enumerate(compras) if r["CLUE"] not in clues]
    clave_orphans = [i for i, r in enumerate(compras) if r["CLAVE"] not in claves]
    total = round(ORPHAN_RATE * LINEAS)
    assert not set(clue_orphans) & set(clave_orphans)
    assert len(clue_orphans) + len(clave_orphans) == total
    assert len(clue_orphans) == round(total * PROPORCION_CLUE)
    manifest = json.loads((full_dataset / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["orphans"] == {"CLAVE": len(clave_orphans), "CLUE": len(clue_orphans)}


def test_zero_rate_has_no_orphans(run_gen, read_table, small_config, tmp_path):
    text = small_config.read_text(encoding="utf-8").replace(
        "orphan_rate = 0.005", "orphan_rate = 0.0"
    )
    config = tmp_path / "zero.toml"
    config.write_text(text, encoding="utf-8")
    out = tmp_path / "out"
    proc = run_gen("generate", "--config", str(config), "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    clues = {r["CLUE"] for r in read_table(out / "CLUE_CAT.csv")[1]}
    claves = {r["CLAVE"] for r in read_table(out / "CUADRO_BASICO.csv")[1]}
    compras = read_table(out / "COMPRAS.csv")[1]
    assert all(r["CLUE"] in clues and r["CLAVE"] in claves for r in compras)
    assert json.loads((Path(out) / "manifest.json").read_text())["orphans"] == {
        "CLAVE": 0,
        "CLUE": 0,
    }
