"""CLUE_CAT: synthetic medical units with real geography and institutions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from generator.config import NIVELES_ATENCION, Config
from generator.reference import Entidad, Institucion, Reference

CONSECUTIVO_MAX = 999_999


@dataclass(frozen=True)
class Unit:
    clue: str
    entidad: str
    cve_ent: str
    institucion: str
    delegacion: str
    grupo_institucional: str
    nivel_atencion: str
    municipio: str


def _largest_remainder(total: int, weights: np.ndarray, minimum: int = 0) -> np.ndarray:
    """Integer split of total proportional to weights, each part at least minimum."""
    base = np.full(len(weights), minimum, dtype=np.int64)
    rest = total - int(base.sum())
    if rest < 0:
        raise ValueError("total menor que el mínimo por grupo")
    shares = weights / weights.sum() * rest
    counts = np.floor(shares).astype(np.int64)
    remainder = rest - int(counts.sum())
    order = np.lexsort((np.arange(len(weights)), -(shares - counts)))
    counts[order[:remainder]] += 1
    return base + counts


def build_units(config: Config, reference: Reference, rng: np.random.Generator) -> tuple[Unit, ...]:
    """Spread the configured units over institutions and entities and build their CLUES."""
    instituciones = reference.instituciones
    shares = np.array(
        [config.concentracion.participacion_institucion[i.institucion] for i in instituciones]
    )
    per_institution = _largest_remainder(config.volumen.unidades_medicas, shares, minimum=1)
    municipios_by_ent: dict[str, list] = {}
    for m in reference.municipios:
        municipios_by_ent.setdefault(m.cve_ent, []).append(m)
    niveles = np.array(NIVELES_ATENCION)
    nivel_p = np.array([config.concentracion.reparto_nivel[n] for n in NIVELES_ATENCION])

    units: list[Unit] = []
    for institucion, count in zip(instituciones, per_institution, strict=True):
        entidades: list[Entidad] = [
            e for e in reference.entidades if reference.entidad_presente(e, institucion)
        ]
        weights = np.array([e.poblacion for e in entidades], dtype=float)
        weights = weights**config.concentracion.beta_entidades
        per_entity = _largest_remainder(
            int(count), weights, minimum=1 if count >= len(entidades) else 0
        )
        for entidad, n in zip(entidades, per_entity, strict=True):
            if n == 0:
                continue
            units.extend(
                _units_for(institucion, entidad, int(n), municipios_by_ent, niveles, nivel_p, rng)
            )
    return tuple(sorted(units, key=lambda u: u.clue))


def _units_for(
    institucion: Institucion,
    entidad: Entidad,
    n: int,
    municipios_by_ent: dict[str, list],
    niveles: np.ndarray,
    nivel_p: np.ndarray,
    rng: np.random.Generator,
) -> list[Unit]:
    municipios = municipios_by_ent[entidad.cve_ent]
    pob = np.array([m.poblacion for m in municipios], dtype=float)
    consecutivos = rng.choice(CONSECUTIVO_MAX, size=n, replace=False) + 1
    nivel_idx = rng.choice(len(niveles), size=n, p=nivel_p)
    mun_idx = rng.choice(len(municipios), size=n, p=pob / pob.sum())
    prefix = entidad.codigo_clues + institucion.prefijo_clues
    return [
        Unit(
            clue=f"{prefix}{int(c):06d}",
            entidad=entidad.entidad,
            cve_ent=entidad.cve_ent,
            institucion=institucion.institucion,
            delegacion=f"{institucion.prefijo_delegacion} {entidad.entidad}",
            grupo_institucional=institucion.grupo_institucional,
            nivel_atencion=str(niveles[k]),
            municipio=municipios[j].municipio,
        )
        for c, k, j in zip(consecutivos, nivel_idx, mun_idx, strict=True)
    ]
