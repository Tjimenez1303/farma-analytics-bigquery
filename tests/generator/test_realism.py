"""Realism of geography, institutions, catalog, brands and prices (US3, SC-005 to SC-008)."""

from __future__ import annotations

import collections
import datetime as dt

from generator.supplies import contains_real_lab

GRUPOS = {"Seguridad social", "Fuerzas Armadas y PEMEX", "Población sin seguridad social"}
NIVELES = {"Primer nivel", "Segundo nivel", "Tercer nivel"}


def _cents(importe: str) -> int:
    pesos, centavos = importe.split(".")
    return int(pesos) * 100 + int(centavos)


def test_entidades_are_the_32_official_names(full_tables, full_model):
    official = {e.entidad for e in full_model["reference"].entidades}
    assert len(official) == 32
    assert {r["ENTIDAD"] for r in full_tables["CLUE_CAT"]} == official


def test_clue_prefixes_match_entity_and_institution(full_tables, full_model):
    ref = full_model["reference"]
    code = {e.entidad: e.codigo_clues for e in ref.entidades}
    prefix = {i.institucion: i.prefijo_clues for i in ref.instituciones}
    for r in full_tables["CLUE_CAT"]:
        assert r["CLUE"][:2] == code[r["ENTIDAD"]]
        assert r["CLUE"][2:5] == prefix[r["INSTITUCION"]]


def test_institution_presence_by_entity(full_tables, full_model):
    ref = full_model["reference"]
    entidades = {e.entidad: e for e in ref.entidades}
    instituciones = {i.institucion: i for i in ref.instituciones}
    for r in full_tables["CLUE_CAT"]:
        assert ref.entidad_presente(entidades[r["ENTIDAD"]], instituciones[r["INSTITUCION"]])


def test_groups_levels_municipios_and_delegaciones(full_tables, full_model):
    ref = full_model["reference"]
    rows = full_tables["CLUE_CAT"]
    assert {r["GRUPO_INSTITUCIONAL"] for r in rows} == GRUPOS
    group_of = collections.defaultdict(set)
    for r in rows:
        group_of[r["INSTITUCION"]].add(r["GRUPO_INSTITUCIONAL"])
    assert all(len(g) == 1 for g in group_of.values())
    niveles = collections.Counter(r["NIVEL_ATENCION"] for r in rows)
    assert set(niveles) == NIVELES
    assert niveles["Primer nivel"] > niveles["Tercer nivel"]
    cve = {e.entidad: e.cve_ent for e in ref.entidades}
    municipios = {(m.cve_ent, m.municipio) for m in ref.municipios}
    delegacion = {i.institucion: i.prefijo_delegacion for i in ref.instituciones}
    for r in rows:
        assert (cve[r["ENTIDAD"]], r["MUNICIPIO"]) in municipios
        assert r["DELEGACION"] == f"{delegacion[r['INSTITUCION']]} {r['ENTIDAD']}"


def test_catalog_descriptions_and_groups(full_tables, full_model):
    ref = {m.molecula: m for m in full_model["reference"].moleculas}
    group_of = collections.defaultdict(set)
    for r in full_tables["CUADRO_BASICO"]:
        group_of[r["MOLECULA"]].add(r["GRUPO_TERAPEUTICO"])
        assert r["DESCRIPCION"].startswith(r["MOLECULA"])
        assert any(
            p.concentracion in r["DESCRIPCION"] and p.concentracion in r["PRESENTACION"]
            for p in ref[r["MOLECULA"]].presentaciones
        )
    assert all(len(g) == 1 for g in group_of.values())


def test_brands_manufacturers_and_suppliers(full_tables, full_model):
    supplies = full_model["supplies"]
    labs = full_model["reference"].laboratorios_reales
    claves = {r["CLAVE"]: r for r in full_tables["CUADRO_BASICO"]}
    fab_of_brand = collections.defaultdict(set)
    fabs_by_clave = collections.defaultdict(set)
    for r in full_tables["COMPRAS"]:
        fab_of_brand[r["MARCA"]].add(r["FABRICANTE"])
        assert r["COD_PROVEEDOR"] in supplies.proveedores[r["FABRICANTE"]]
        if r["CLAVE"] in claves:
            molecula = claves[r["CLAVE"]]["MOLECULA"]
            assert r["FABRICANTE"] in supplies.autorizados[molecula]
            fabs_by_clave[r["CLAVE"]].add(r["FABRICANTE"])
    assert all(len(f) == 1 for f in fab_of_brand.values())
    for clave, r in claves.items():
        assert supplies.fabricantes[r["FABRICANTE"]].innovador
        if fabs_by_clave[clave]:
            assert r["FABRICANTE"] in fabs_by_clave[clave]
    assert not any(contains_real_lab(f, labs) for f in supplies.fabricantes)


def test_unit_price_inside_band(full_tables, full_model):
    bands = {c.clave: (c.banda_min, c.banda_max) for c in full_model["supplies"].claves}
    for r in full_tables["COMPRAS"]:
        if r["CLAVE"] not in bands:
            continue
        low, high = bands[r["CLAVE"]]
        price = _cents(r["IMPORTE"]) / int(r["PIEZAS"])
        assert low - 1 <= price <= high + 1


def test_concentration(full_tables):
    molecula = {r["CLAVE"]: r["MOLECULA"] for r in full_tables["CUADRO_BASICO"]}
    institucion = {r["CLUE"]: r["INSTITUCION"] for r in full_tables["CLUE_CAT"]}
    by_mol, by_inst = collections.Counter(), collections.Counter()
    for r in full_tables["COMPRAS"]:
        cents = _cents(r["IMPORTE"])
        if r["CLAVE"] in molecula:
            by_mol[molecula[r["CLAVE"]]] += cents
        if r["CLUE"] in institucion:
            by_inst[institucion[r["CLUE"]]] += cents
    values = sorted(by_mol.values(), reverse=True)
    top = values[: max(1, round(0.2 * len(values)))]
    assert 0.60 <= sum(top) / sum(values) <= 0.90
    assert max(by_inst.values()) / sum(by_inst.values()) > 0.30


def test_seasonality(full_tables):
    by_month = collections.Counter()
    for r in full_tables["COMPRAS"]:
        day = dt.date.fromisoformat(r["FECHA"])
        by_month[(day.year, day.month)] += _cents(r["IMPORTE"])
    assert set(by_month) == {(y, m) for y in (2024, 2025) for m in range(1, 13)}
    for year in (2024, 2025):
        months = [by_month[(year, m)] for m in range(1, 13)]
        assert max(months) / min(months) >= 1.2
