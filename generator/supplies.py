"""CUADRO_BASICO plus fictitious manufacturers, brands, suppliers and prices."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass

import numpy as np
from faker import Faker

from generator.config import Config
from generator.reference import Molecula, Presentacion, Reference

ESPECIFICO_MIN, ESPECIFICO_MAX = 100, 6999
SYLLABLES = (
    "ka",
    "lo",
    "mi",
    "ra",
    "ne",
    "to",
    "vi",
    "sa",
    "du",
    "fe",
    "ri",
    "no",
    "ze",
    "pa",
    "lu",
    "ti",
    "ro",
    "ma",
    "xe",
    "bri",
    "cor",
    "dal",
    "fen",
    "gal",
    "lin",
    "mor",
    "nax",
    "pril",
    "quin",
    "sel",
    "tor",
    "vex",
)
BRAND_ENDINGS = ("", "n", "x", "l", "r", "s")


@dataclass(frozen=True)
class Fabricante:
    nombre: str
    innovador: bool
    factor: float


@dataclass(frozen=True)
class Clave:
    clave: str
    descripcion: str
    molecula: str
    grupo_terapeutico: str
    presentacion: str
    fabricante: str
    base_centavos: int
    banda_min: float
    banda_max: float


@dataclass(frozen=True)
class Supplies:
    claves: tuple[Clave, ...]
    fabricantes: dict[str, Fabricante]
    autorizados: dict[str, tuple[str, ...]]
    marcas: dict[tuple[str, str], str]
    proveedores: dict[str, tuple[str, ...]]
    especificos_usados: frozenset[int]


def normalize(text: str) -> str:
    """Lowercase ASCII words separated by single spaces."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text.lower()))


def contains_real_lab(name: str, real_labs: tuple[str, ...]) -> bool:
    """Whether a whole-word sequence of any real lab name appears in name."""
    words = f" {normalize(name)} "
    return any(f" {normalize(lab)} " in words for lab in real_labs)


def descripcion(molecula: Molecula, p: Presentacion) -> str:
    return (
        f"{molecula.molecula}. {p.forma}. Cada {p.unidad} contiene: "
        f"{molecula.molecula.lower()} {p.concentracion}. {p.envase}."
    )


def presentacion_text(p: Presentacion) -> str:
    return f"{p.forma} {p.concentracion}. {p.envase}"


def _manufacturer_names(
    n_innovadores: int, n_genericos: int, faker: Faker, real_labs: tuple[str, ...]
) -> tuple[list[str], list[str]]:
    seen: set[str] = set()

    def unique(pattern: str, surnames: int) -> str:
        while True:
            parts = [faker.last_name() for _ in range(surnames)]
            if len(set(parts)) != len(parts):
                continue
            name = pattern.format(*parts)
            if name not in seen and not contains_real_lab(name, real_labs):
                seen.add(name)
                return name

    innovadores = [unique("Laboratorios {} {}, S.A. de C.V.", 2) for _ in range(n_innovadores)]
    genericos = []
    for i in range(n_genericos):
        pattern = "Farmacéutica {}, S.A. de C.V." if i % 2 == 0 else "Genéricos {}, S.A. de C.V."
        genericos.append(unique(pattern, 1))
    return innovadores, genericos


def _brand(rng: np.random.Generator, used: set[str]) -> str:
    while True:
        size = int(rng.integers(2, 4))
        idx = rng.integers(0, len(SYLLABLES), size=size)
        ending = BRAND_ENDINGS[int(rng.integers(0, len(BRAND_ENDINGS)))]
        name = ("".join(SYLLABLES[i] for i in idx) + ending).capitalize()
        if name not in used:
            used.add(name)
            return name


def build_supplies(
    config: Config,
    reference: Reference,
    supplies_rng: np.random.Generator,
    companies_rng: np.random.Generator,
    faker: Faker,
) -> Supplies:
    """Catalog keys, fictitious companies with one price factor each, brands and suppliers."""
    vol, pre = config.volumen, config.precios
    innov_names, gen_names = _manufacturer_names(
        vol.fabricantes_innovadores, vol.fabricantes_genericos, faker, reference.laboratorios_reales
    )
    f_ref = companies_rng.uniform(*pre.factor_referencia, size=len(innov_names))
    f_gen = companies_rng.uniform(*pre.factor_generico, size=len(gen_names))
    fabricantes = {
        n: Fabricante(n, True, float(f)) for n, f in zip(innov_names, f_ref, strict=True)
    }
    fabricantes |= {
        n: Fabricante(n, False, float(f)) for n, f in zip(gen_names, f_gen, strict=True)
    }

    codes = companies_rng.choice(99_999, size=vol.proveedores, replace=False) + 1
    cod_proveedores = sorted(f"PRV{int(c):05d}" for c in codes)
    proveedores: dict[str, tuple[str, ...]] = {}
    for nombre in innov_names + gen_names:
        k = int(
            companies_rng.integers(
                vol.proveedores_por_fabricante[0], vol.proveedores_por_fabricante[1] + 1
            )
        )
        picks = companies_rng.choice(len(cod_proveedores), size=k, replace=False)
        proveedores[nombre] = tuple(sorted(cod_proveedores[i] for i in picks))

    autorizados: dict[str, tuple[str, ...]] = {}
    marcas: dict[tuple[str, str], str] = {}
    used_brands: set[str] = set()
    g_min, g_max = vol.genericos_por_molecula
    for mol in reference.moleculas:
        ref = innov_names[int(companies_rng.integers(0, len(innov_names)))]
        k = int(companies_rng.integers(g_min, g_max + 1))
        gens = [gen_names[i] for i in companies_rng.choice(len(gen_names), size=k, replace=False)]
        autorizados[mol.molecula] = (ref, *gens)
        for fab in autorizados[mol.molecula]:
            marcas[(fab, mol.molecula)] = _brand(companies_rng, used_brands)

    presentaciones = [(m, p) for m in reference.moleculas for p in m.presentaciones]
    especificos = (
        supplies_rng.choice(
            ESPECIFICO_MAX - ESPECIFICO_MIN + 1, size=len(presentaciones), replace=False
        )
        + ESPECIFICO_MIN
    )
    claves: list[Clave] = []
    for (mol, p), esp in zip(presentaciones, especificos, strict=True):
        low, high = pre.nivel[mol.nivel_precio]
        base = int(np.rint(math.exp(supplies_rng.uniform(math.log(low), math.log(high))) * 100))
        factors = [fabricantes[f].factor for f in autorizados[mol.molecula]]
        claves.append(
            Clave(
                clave=f"010.000.{int(esp):04d}.00",
                descripcion=descripcion(mol, p),
                molecula=mol.molecula,
                grupo_terapeutico=mol.grupo_terapeutico,
                presentacion=presentacion_text(p),
                fabricante=autorizados[mol.molecula][0],
                base_centavos=base,
                banda_min=base * min(factors) * (1 - pre.ruido_max),
                banda_max=base * max(factors) * (1 + pre.ruido_max),
            )
        )
    return Supplies(
        claves=tuple(sorted(claves, key=lambda c: c.clave)),
        fabricantes=fabricantes,
        autorizados=autorizados,
        marcas=marcas,
        proveedores=proveedores,
        especificos_usados=frozenset(int(e) for e in especificos),
    )
