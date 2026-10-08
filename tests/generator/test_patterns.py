"""Injected commercial patterns P3, P4 and P5 (FR-018a, SC-007a)."""

from __future__ import annotations

import collections


def _cents(importe: str) -> int:
    pesos, centavos = importe.split(".")
    return int(pesos) * 100 + int(centavos)


def _lines(full_tables):
    claves = {r["CLAVE"]: r for r in full_tables["CUADRO_BASICO"]}
    units = {r["CLUE"]: r for r in full_tables["CLUE_CAT"]}
    for r in full_tables["COMPRAS"]:
        if r["CLAVE"] in claves and r["CLUE"] in units:
            yield r, claves[r["CLAVE"]], units[r["CLUE"]]


def test_p3_price_by_institution(full_tables, full_model):
    molecula = full_model["config"].p3.molecula_ejemplo
    supplies = full_model["supplies"]
    reference = supplies.autorizados[molecula][0]
    stats = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r, clave, unit in _lines(full_tables):
        if clave["MOLECULA"] != molecula:
            continue
        s = stats[unit["INSTITUCION"]]
        s[0] += _cents(r["IMPORTE"])
        s[1] += int(r["PIEZAS"])
        s[2] += r["FABRICANTE"] == reference
        s[3] += 1
    share = {i: s[2] / s[3] for i, s in stats.items()}
    price = {i: s[0] / s[1] for i, s in stats.items()}
    most, least = max(share, key=share.get), min(share, key=share.get)
    assert price[most] >= 1.2 * price[least]


def test_p4_group_growth(full_tables, full_model):
    grupo = next(iter(full_model["config"].p4.factor_2025))
    totals = collections.Counter()
    for r, clave, _unit in _lines(full_tables):
        key = "grupo" if clave["GRUPO_TERAPEUTICO"] == grupo else "resto"
        totals[(key, r["FECHA"][:4])] += _cents(r["IMPORTE"])
    growth_g = totals[("grupo", "2025")] / totals[("grupo", "2024")] - 1
    growth_r = totals[("resto", "2025")] / totals[("resto", "2024")] - 1
    assert growth_g - growth_r >= 0.10


def test_p5_generic_share_gain(full_tables, full_model):
    supplies = full_model["supplies"]
    for molecula in full_model["config"].p5.moleculas:
        totals = collections.Counter()
        for r, clave, _unit in _lines(full_tables):
            if clave["MOLECULA"] == molecula:
                totals[(r["FABRICANTE"], r["FECHA"][:4])] += _cents(r["IMPORTE"])
        year_total = {
            y: sum(v for (f, yy), v in totals.items() if yy == y) for y in ("2024", "2025")
        }

        def share(fab, year, totals=totals, year_total=year_total):
            return totals[(fab, year)] / year_total[year]

        reference, *generics = supplies.autorizados[molecula]
        gains = {g: share(g, "2025") - share(g, "2024") for g in generics}
        assert max(gains.values()) >= 0.10, molecula
        assert share(reference, "2025") < share(reference, "2024"), molecula


def test_pattern_molecules_have_high_spend(full_tables, full_model):
    config = full_model["config"]
    by_mol = collections.Counter()
    for r, clave, _unit in _lines(full_tables):
        by_mol[clave["MOLECULA"]] += _cents(r["IMPORTE"])
    ranked = [m for m, _ in by_mol.most_common()]
    top = set(ranked[: max(1, round(0.2 * len(ranked)))])
    for molecula in (config.p3.molecula_ejemplo, *config.p5.moleculas):
        assert molecula in top, molecula
