"""Domains of PIEZAS, IMPORTE and FECHA (FR-030, SC-005)."""

from __future__ import annotations

import datetime as dt

PIEZAS_MAX = 50_000
INICIO, FIN = dt.date(2024, 1, 1), dt.date(2025, 12, 31)


def _cents(importe: str) -> int:
    pesos, centavos = importe.split(".")
    return int(pesos) * 100 + int(centavos)


def test_piezas_range(full_tables):
    assert all(1 <= int(r["PIEZAS"]) <= PIEZAS_MAX for r in full_tables["COMPRAS"])


def test_importe_positive_and_divisible(full_tables):
    for r in full_tables["COMPRAS"]:
        cents = _cents(r["IMPORTE"])
        assert cents > 0
        assert cents % int(r["PIEZAS"]) == 0


def test_fecha_in_period_and_weekday(full_tables):
    for r in full_tables["COMPRAS"]:
        day = dt.date.fromisoformat(r["FECHA"])
        assert INICIO <= day <= FIN
        assert day.weekday() < 5
