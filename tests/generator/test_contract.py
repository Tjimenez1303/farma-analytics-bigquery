"""Contract of the three CSV files (FR-001 to FR-004, contracts/csv-format.md)."""

from __future__ import annotations

import re

import pytest

HEADERS = {
    "COMPRAS.csv": "CLUE,CLAVE,COD_PROVEEDOR,MARCA,FABRICANTE,PIEZAS,IMPORTE,FECHA",
    "CLUE_CAT.csv": "CLUE,ENTIDAD,INSTITUCION,DELEGACION,GRUPO_INSTITUCIONAL,NIVEL_ATENCION,MUNICIPIO",
    "CUADRO_BASICO.csv": "CLAVE,DESCRIPCION,MOLECULA,GRUPO_TERAPEUTICO,PRESENTACION,FABRICANTE",
}
CLUE_RE = re.compile(r"^[A-Z]{2}(IMS|IST|SDN|SMA|PMX|IMO|SSA)[0-9]{6}$")
CLAVE_RE = re.compile(r"^010\.000\.[0-9]{4}\.[0-9]{2}$")
PATTERNS = {
    "COD_PROVEEDOR": re.compile(r"^PRV[0-9]{5}$"),
    "IMPORTE": re.compile(r"^[0-9]+\.[0-9]{2}$"),
    "FECHA": re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"),
    "PIEZAS": re.compile(r"^[0-9]+$"),
}


@pytest.mark.parametrize("name", sorted(HEADERS))
def test_header_and_encoding(full_dataset, name):
    raw = (full_dataset / name).read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert raw.split(b"\n", 1)[0].decode("utf-8") == HEADERS[name]
    raw.decode("utf-8")


def test_key_formats(full_tables):
    assert all(CLUE_RE.match(r["CLUE"]) for r in full_tables["CLUE_CAT"])
    assert all(CLUE_RE.match(r["CLUE"]) for r in full_tables["COMPRAS"])
    assert all(CLAVE_RE.match(r["CLAVE"]) for r in full_tables["CUADRO_BASICO"])
    assert all(CLAVE_RE.match(r["CLAVE"]) for r in full_tables["COMPRAS"])


@pytest.mark.parametrize("field", sorted(PATTERNS))
def test_purchase_field_formats(full_tables, field):
    pattern = PATTERNS[field]
    assert all(pattern.match(r[field]) for r in full_tables["COMPRAS"])


def test_no_newlines_inside_fields(full_tables):
    for rows in full_tables.values():
        assert not any("\n" in v or "\r" in v for r in rows for v in r.values())


def test_row_order(full_tables):
    clue_cat = [r["CLUE"] for r in full_tables["CLUE_CAT"]]
    cuadro = [r["CLAVE"] for r in full_tables["CUADRO_BASICO"]]
    assert clue_cat == sorted(clue_cat)
    assert cuadro == sorted(cuadro)
    keys = [(r["FECHA"], r["CLUE"], r["CLAVE"]) for r in full_tables["COMPRAS"]]
    assert keys == sorted(keys)
