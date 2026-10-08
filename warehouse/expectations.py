"""Expected values of the quality checks, read from the generator manifest and configuration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

from generator.config import load_config
from generator.manifest import load as load_manifest
from generator.reference import load_reference
from warehouse.bq import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "generator" / "config.toml"
MANIFEST_PATH = REPO_ROOT / "generator" / "manifest.json"

_ROW_PARAMETERS = {
    "filas_compras": "COMPRAS.csv",
    "filas_clue_cat": "CLUE_CAT.csv",
    "filas_cuadro_basico": "CUADRO_BASICO.csv",
}
_DISPERSION_STEP = Decimal("0.000001")


@dataclass(frozen=True)
class Parameter:
    name: str
    type: str  # GoogleSQL type of the bq query parameter
    value: str


def _decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def load_expectations(
    config_path: Path = CONFIG_PATH, manifest_path: Path = MANIFEST_PATH
) -> dict[str, Parameter]:
    """Query parameters of the checks: row and orphan counts, period and price bounds."""
    manifest = load_manifest(manifest_path)
    rows = {entry["name"]: entry["rows"] for entry in manifest["files"]}
    config = load_config(Path(config_path), load_reference())
    prices = config.precios

    noise = _decimal(prices.ruido_max)
    lowest_generic = _decimal(prices.factor_generico[0])
    highest_reference = _decimal(prices.factor_referencia[1])
    lowest_base = min(_decimal(low) for low, _ in prices.nivel.values())
    highest_base = max(_decimal(high) for _, high in prices.nivel.values())

    precio_minimo = lowest_base * lowest_generic * (1 - noise)
    precio_maximo = highest_base * highest_reference * (1 + noise)
    dispersion = (highest_reference * (1 + noise)) / (lowest_generic * (1 - noise))
    dispersion = dispersion.quantize(_DISPERSION_STEP, rounding=ROUND_CEILING)

    params = [
        *(Parameter(name, "INT64", str(rows[file])) for name, file in _ROW_PARAMETERS.items()),
        Parameter("huerfanos_clue", "INT64", str(manifest["orphans"]["CLUE"])),
        Parameter("huerfanos_clave", "INT64", str(manifest["orphans"]["CLAVE"])),
        Parameter("fecha_inicio", "DATE", config.periodo.inicio.isoformat()),
        Parameter("fecha_fin", "DATE", config.periodo.fin.isoformat()),
        Parameter("precio_minimo", "NUMERIC", _plain(precio_minimo)),
        Parameter("precio_maximo", "NUMERIC", _plain(precio_maximo)),
        Parameter("dispersion_maxima", "NUMERIC", _plain(dispersion)),
    ]
    return {p.name: p for p in params}


def as_bq_parameters(expectations: dict[str, Parameter], names: Iterable[str]) -> list[str]:
    """--parameter=NAME:TYPE:VALUE flags for the given names, in the given order."""
    return [f"--parameter={p.name}:{p.type}:{p.value}" for p in (expectations[n] for n in names)]
