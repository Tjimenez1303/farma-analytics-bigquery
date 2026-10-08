"""Readers for the versioned reference catalogs in generator/reference/."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"


class ReferenceError(Exception):
    """A reference catalog is missing or malformed."""


@dataclass(frozen=True)
class Entidad:
    cve_ent: str
    entidad: str
    codigo_clues: str
    poblacion: int
    imss_bienestar: bool
    sedena: bool
    semar: bool
    pemex: bool


@dataclass(frozen=True)
class Municipio:
    cve_ent: str
    cve_mun: str
    municipio: str
    poblacion: int


@dataclass(frozen=True)
class Institucion:
    institucion: str
    prefijo_clues: str
    grupo_institucional: str
    prefijo_delegacion: str
    presencia: str


@dataclass(frozen=True)
class Presentacion:
    forma: str
    unidad: str
    concentracion: str
    envase: str


@dataclass(frozen=True)
class Molecula:
    molecula: str
    grupo_terapeutico: str
    nivel_precio: str
    presentaciones: tuple[Presentacion, ...]


@dataclass(frozen=True)
class Reference:
    entidades: tuple[Entidad, ...]
    municipios: tuple[Municipio, ...]
    instituciones: tuple[Institucion, ...]
    moleculas: tuple[Molecula, ...]
    laboratorios_reales: tuple[str, ...]

    def entidad_presente(self, entidad: Entidad, institucion: Institucion) -> bool:
        """Whether the institution operates units in the entity."""
        flags = {
            "todas": True,
            "sedena": entidad.sedena,
            "semar": entidad.semar,
            "pemex": entidad.pemex,
            "imss_bienestar": entidad.imss_bienestar,
            "no_imss_bienestar": not entidad.imss_bienestar,
        }
        return flags[institucion.presencia]


def _read_rows(path: Path, columns: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ReferenceError(f"Falta el catálogo de referencia {path}.")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in columns if c not in (reader.fieldnames or [])]
        if missing:
            raise ReferenceError(f"{path.name}: faltan las columnas {', '.join(missing)}.")
        return list(reader)


def _flag(value: str) -> bool:
    return value == "1"


def _presentacion(text: str) -> Presentacion:
    parts = text.split(";")
    if len(parts) != 4:
        raise ReferenceError(f"moleculas.csv: presentación mal formada: {text!r}.")
    return Presentacion(*parts)


def load_reference(directory: Path = REFERENCE_DIR) -> Reference:
    """Load every reference catalog, sorted by its key."""
    entidades = tuple(
        Entidad(
            r["cve_ent"],
            r["entidad"],
            r["codigo_clues"],
            int(r["poblacion_2020"]),
            _flag(r["imss_bienestar"]),
            _flag(r["sedena"]),
            _flag(r["semar"]),
            _flag(r["pemex"]),
        )
        for r in _read_rows(
            directory / "entidades.csv",
            [
                "cve_ent",
                "entidad",
                "codigo_clues",
                "poblacion_2020",
                "imss_bienestar",
                "sedena",
                "semar",
                "pemex",
            ],
        )
    )
    municipios = tuple(
        Municipio(r["cve_ent"], r["cve_mun"], r["municipio"], int(r["poblacion_2020"]))
        for r in _read_rows(
            directory / "municipios.csv", ["cve_ent", "cve_mun", "municipio", "poblacion_2020"]
        )
    )
    instituciones = tuple(
        Institucion(
            r["institucion"],
            r["prefijo_clues"],
            r["grupo_institucional"],
            r["prefijo_delegacion"],
            r["presencia"],
        )
        for r in _read_rows(
            directory / "instituciones.csv",
            [
                "institucion",
                "prefijo_clues",
                "grupo_institucional",
                "prefijo_delegacion",
                "presencia",
            ],
        )
    )
    moleculas = tuple(
        Molecula(
            r["molecula"],
            r["grupo_terapeutico"],
            r["nivel_precio"],
            tuple(_presentacion(p) for p in r["presentaciones"].split("|")),
        )
        for r in _read_rows(
            directory / "moleculas.csv",
            ["molecula", "grupo_terapeutico", "nivel_precio", "presentaciones"],
        )
    )
    labs_path = directory / "laboratorios_reales.txt"
    if not labs_path.is_file():
        raise ReferenceError(f"Falta el catálogo de referencia {labs_path}.")
    laboratorios = tuple(
        line.strip() for line in labs_path.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    return Reference(
        entidades=tuple(sorted(entidades, key=lambda e: e.cve_ent)),
        municipios=tuple(sorted(municipios, key=lambda m: (m.cve_ent, m.cve_mun))),
        instituciones=instituciones,
        moleculas=tuple(sorted(moleculas, key=lambda m: m.molecula)),
        laboratorios_reales=tuple(sorted(laboratorios)),
    )
