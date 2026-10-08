"""Loading and validation of generator/config.toml."""

from __future__ import annotations

import datetime as dt
import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generator.reference import Reference

NIVELES_ATENCION = ("Primer nivel", "Segundo nivel", "Tercer nivel")


class ConfigError(Exception):
    """Invalid configuration value. The CLI maps it to exit code 2."""


@dataclass(frozen=True)
class Periodo:
    inicio: dt.date
    fin: dt.date
    solo_dias_laborables: bool


@dataclass(frozen=True)
class Volumen:
    lineas_compra: int
    unidades_medicas: int
    fabricantes_innovadores: int
    fabricantes_genericos: int
    proveedores: int
    genericos_por_molecula: tuple[int, int]
    proveedores_por_fabricante: tuple[int, int]
    piezas_max: int


@dataclass(frozen=True)
class Huerfanos:
    orphan_rate: float
    proporcion_clue: float


@dataclass(frozen=True)
class Concentracion:
    alpha_moleculas: float
    moleculas_destacadas: dict[str, int]
    beta_entidades: float
    participacion_institucion: dict[str, float]
    reparto_nivel: dict[str, float]
    peso_compra_nivel: dict[str, float]


@dataclass(frozen=True)
class Estacionalidad:
    factores_mes: tuple[float, ...]
    crecimiento_total: float


@dataclass(frozen=True)
class Precios:
    nivel: dict[str, tuple[float, float]]
    factor_referencia: tuple[float, float]
    factor_generico: tuple[float, float]
    ruido_max: float
    piezas_mu: float
    piezas_sigma: float


@dataclass(frozen=True)
class PatronP3:
    molecula_ejemplo: str
    prob_referencia: dict[str, float]


@dataclass(frozen=True)
class PatronP4:
    factor_2025: dict[str, float]
    factor_2025_resto: float


@dataclass(frozen=True)
class PatronP5:
    moleculas: tuple[str, ...]
    cuota_generico_inicial: float
    cuota_generico_final: float


@dataclass(frozen=True)
class Config:
    seed: str
    periodo: Periodo
    volumen: Volumen
    huerfanos: Huerfanos
    concentracion: Concentracion
    estacionalidad: Estacionalidad
    precios: Precios
    p3: PatronP3
    p4: PatronP4
    p5: PatronP5
    raw: bytes


SCHEMA: dict[str, set[str]] = {
    "": {
        "seed",
        "periodo",
        "volumen",
        "huerfanos",
        "concentracion",
        "estacionalidad",
        "precios",
        "patrones",
    },
    "periodo": {"inicio", "fin", "solo_dias_laborables"},
    "volumen": {
        "lineas_compra",
        "unidades_medicas",
        "fabricantes_innovadores",
        "fabricantes_genericos",
        "proveedores",
        "genericos_por_molecula",
        "proveedores_por_fabricante",
        "piezas_max",
    },
    "huerfanos": {"orphan_rate", "proporcion_clue"},
    "concentracion": {
        "alpha_moleculas",
        "moleculas_destacadas",
        "beta_entidades",
        "participacion_institucion",
        "reparto_nivel",
        "peso_compra_nivel",
    },
    "estacionalidad": {"factores_mes", "crecimiento_total"},
    "precios": {"nivel", "factor_referencia", "factor_generico", "ruido_max", "piezas_lognormal"},
    "precios.piezas_lognormal": {"mu", "sigma"},
    "patrones": {"p3", "p4", "p5"},
    "patrones.p3": {"molecula_ejemplo", "prob_referencia"},
    "patrones.p4": {"factor_2025", "factor_2025_resto"},
    "patrones.p5": {"moleculas", "cuota_generico_inicial", "cuota_generico_final"},
}


def _fail(path: str, value: Any, rule: str) -> ConfigError:
    return ConfigError(f"{path}: valor {value!r} fuera de rango {rule}")


def _table(data: dict[str, Any], path: str) -> dict[str, Any]:
    keys = path.split(".") if path else []
    node: Any = data
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            raise ConfigError(f"{path}: falta la tabla en la configuración")
        node = node[key]
    if not isinstance(node, dict):
        raise ConfigError(f"{path}: debe ser una tabla")
    unknown = sorted(set(node) - SCHEMA[path])
    if unknown:
        where = f"{path}." if path else ""
        raise ConfigError(f"{where}{unknown[0]}: clave desconocida en la configuración")
    missing = sorted(SCHEMA[path] - set(node))
    if missing:
        where = f"{path}." if path else ""
        raise ConfigError(f"{where}{missing[0]}: falta el parámetro en la configuración")
    return node


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigError(f"{path}: valor {value!r} debe ser un número")
    return float(value)


def _int(value: Any, path: str, low: int, high: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{path}: valor {value!r} debe ser un entero")
    if value < low or (high is not None and value > high):
        rule = f"[{low}, {high}]" if high is not None else f">= {low}"
        raise _fail(path, value, rule)
    return value


def _in_range(
    value: Any,
    path: str,
    low: float,
    high: float,
    rule: str,
    low_open: bool = False,
    high_open: bool = False,
) -> float:
    number = _number(value, path)
    too_low = number <= low if low_open else number < low
    too_high = number >= high if high_open else number > high
    if too_low or too_high:
        raise _fail(path, value, rule)
    return number


def _pair(value: Any, path: str, kind: type) -> tuple[Any, Any]:
    if not isinstance(value, list) or len(value) != 2:
        raise ConfigError(f"{path}: valor {value!r} debe ser una lista [min, max]")
    if kind is int:
        low, high = (_int(v, path, 1) for v in value)
    else:
        low, high = (_number(v, path) for v in value)
    if low > high:
        raise _fail(path, value, "[min, max] con min <= max")
    return low, high


def _mapping(value: Any, path: str, expected: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: debe ser una tabla")
    unknown = sorted(set(value) - set(expected))
    if unknown:
        raise ConfigError(f"{path}.{unknown[0]}: clave desconocida")
    missing = [k for k in expected if k not in value]
    if missing:
        raise ConfigError(f"{path}.{missing[0]}: falta el valor")
    return value


def _seed(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise _fail("seed", value, "texto hexadecimal con prefijo 0x")
    try:
        number = int(value, 16)
    except ValueError as exc:
        raise _fail("seed", value, "texto hexadecimal con prefijo 0x") from exc
    if not 0 < number < 2**128:
        raise _fail("seed", value, "de 1 a 128 bits")
    return value


def load_config(path: Path, reference: Reference) -> Config:
    """Read and validate the configuration. Raises ConfigError on the first invalid value."""
    raw = Path(path).read_bytes()
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{path}: TOML inválido ({exc})") from exc

    _table(data, "")
    seed = _seed(data["seed"])

    per = _table(data, "periodo")
    inicio, fin = per["inicio"], per["fin"]
    for key, value in (("inicio", inicio), ("fin", fin)):
        if not isinstance(value, dt.date) or isinstance(value, dt.datetime):
            raise ConfigError(f"periodo.{key}: valor {value!r} debe ser una fecha TOML")
    if (inicio.month, inicio.day) != (1, 1) or (fin.month, fin.day) != (12, 31):
        raise _fail("periodo", f"{inicio} a {fin}", "del 1 de enero al 31 de diciembre")
    if fin.year - inicio.year + 1 < 2:
        raise _fail("periodo", f"{inicio} a {fin}", "al menos dos años calendario completos")
    if not isinstance(per["solo_dias_laborables"], bool):
        raise ConfigError("periodo.solo_dias_laborables: debe ser true o false")
    periodo = Periodo(inicio, fin, per["solo_dias_laborables"])

    vol = _table(data, "volumen")
    volumen = Volumen(
        lineas_compra=_int(vol["lineas_compra"], "volumen.lineas_compra", 1000, 2_000_000),
        unidades_medicas=_int(vol["unidades_medicas"], "volumen.unidades_medicas", 1),
        fabricantes_innovadores=_int(
            vol["fabricantes_innovadores"], "volumen.fabricantes_innovadores", 1
        ),
        fabricantes_genericos=_int(
            vol["fabricantes_genericos"], "volumen.fabricantes_genericos", 1
        ),
        proveedores=_int(vol["proveedores"], "volumen.proveedores", 1, 99_999),
        genericos_por_molecula=_pair(
            vol["genericos_por_molecula"], "volumen.genericos_por_molecula", int
        ),
        proveedores_por_fabricante=_pair(
            vol["proveedores_por_fabricante"], "volumen.proveedores_por_fabricante", int
        ),
        piezas_max=_int(vol["piezas_max"], "volumen.piezas_max", 1),
    )
    if volumen.genericos_por_molecula[1] > volumen.fabricantes_genericos:
        raise _fail(
            "volumen.genericos_por_molecula",
            list(volumen.genericos_por_molecula),
            f"máximo <= volumen.fabricantes_genericos ({volumen.fabricantes_genericos})",
        )
    if volumen.proveedores_por_fabricante[1] > volumen.proveedores:
        raise _fail(
            "volumen.proveedores_por_fabricante",
            list(volumen.proveedores_por_fabricante),
            f"máximo <= volumen.proveedores ({volumen.proveedores})",
        )

    hue = _table(data, "huerfanos")
    huerfanos = Huerfanos(
        orphan_rate=_in_range(hue["orphan_rate"], "huerfanos.orphan_rate", 0, 0.05, "[0, 0.05]"),
        proporcion_clue=_in_range(
            hue["proporcion_clue"], "huerfanos.proporcion_clue", 0, 1, "[0, 1]"
        ),
    )

    instituciones = [i.institucion for i in reference.instituciones]
    moleculas = {m.molecula: m for m in reference.moleculas}
    grupos = {m.grupo_terapeutico for m in reference.moleculas}
    niveles_precio = sorted({m.nivel_precio for m in reference.moleculas})

    con = _table(data, "concentracion")
    participacion = _mapping(
        con["participacion_institucion"], "concentracion.participacion_institucion", instituciones
    )
    for name, value in participacion.items():
        _in_range(
            value,
            f"concentracion.participacion_institucion.{name}",
            0,
            1,
            "(0, 1)",
            low_open=True,
            high_open=True,
        )
    if not math.isclose(sum(participacion.values()), 1.0, abs_tol=1e-9):
        raise _fail(
            "concentracion.participacion_institucion", sum(participacion.values()), "suma igual a 1"
        )
    destacadas = con["moleculas_destacadas"]
    if not isinstance(destacadas, dict):
        raise ConfigError("concentracion.moleculas_destacadas: debe ser una tabla")
    for name, rank in destacadas.items():
        if name not in moleculas:
            raise ConfigError(
                f"concentracion.moleculas_destacadas.{name}: molécula que no existe en "
                "reference/moleculas.csv"
            )
        _int(rank, f"concentracion.moleculas_destacadas.{name}", 1, len(moleculas))
    if len(set(destacadas.values())) != len(destacadas):
        raise _fail("concentracion.moleculas_destacadas", destacadas, "rangos únicos")
    reparto = _mapping(con["reparto_nivel"], "concentracion.reparto_nivel", list(NIVELES_ATENCION))
    for name, value in reparto.items():
        _in_range(
            value,
            f"concentracion.reparto_nivel.{name}",
            0,
            1,
            "(0, 1)",
            low_open=True,
            high_open=True,
        )
    if not math.isclose(sum(reparto.values()), 1.0, abs_tol=1e-9):
        raise _fail("concentracion.reparto_nivel", sum(reparto.values()), "suma igual a 1")
    peso = _mapping(
        con["peso_compra_nivel"], "concentracion.peso_compra_nivel", list(NIVELES_ATENCION)
    )
    for name, value in peso.items():
        if _number(value, f"concentracion.peso_compra_nivel.{name}") <= 0:
            raise _fail(f"concentracion.peso_compra_nivel.{name}", value, "> 0")
    alpha = _number(con["alpha_moleculas"], "concentracion.alpha_moleculas")
    beta = _number(con["beta_entidades"], "concentracion.beta_entidades")
    if alpha <= 0:
        raise _fail("concentracion.alpha_moleculas", alpha, "> 0")
    if beta < 0:
        raise _fail("concentracion.beta_entidades", beta, ">= 0")
    concentracion = Concentracion(
        alpha_moleculas=alpha,
        moleculas_destacadas={k: int(v) for k, v in destacadas.items()},
        beta_entidades=beta,
        participacion_institucion={k: float(participacion[k]) for k in instituciones},
        reparto_nivel={k: float(reparto[k]) for k in NIVELES_ATENCION},
        peso_compra_nivel={k: float(peso[k]) for k in NIVELES_ATENCION},
    )

    est = _table(data, "estacionalidad")
    factores = est["factores_mes"]
    if not isinstance(factores, list) or len(factores) != 12:
        raise _fail("estacionalidad.factores_mes", factores, "doce reales positivos")
    factores_mes = tuple(_number(f, "estacionalidad.factores_mes") for f in factores)
    if min(factores_mes) <= 0:
        raise _fail("estacionalidad.factores_mes", factores, "doce reales positivos")
    estacionalidad = Estacionalidad(
        factores_mes=factores_mes,
        crecimiento_total=_in_range(
            est["crecimiento_total"],
            "estacionalidad.crecimiento_total",
            -0.5,
            1,
            "(-0.5, 1)",
            low_open=True,
            high_open=True,
        ),
    )

    pre = _table(data, "precios")
    nivel = _mapping(pre["nivel"], "precios.nivel", niveles_precio)
    rangos: dict[str, tuple[float, float]] = {}
    for name in niveles_precio:
        low, high = _pair(nivel[name], f"precios.nivel.{name}", float)
        if not 0 < low < high:
            raise _fail(f"precios.nivel.{name}", nivel[name], "0 < min < max")
        rangos[name] = (low, high)
    factor_ref = _pair(pre["factor_referencia"], "precios.factor_referencia", float)
    factor_gen = _pair(pre["factor_generico"], "precios.factor_generico", float)
    if factor_ref[0] <= 0 or factor_gen[0] <= 0:
        raise _fail("precios.factor_referencia", [factor_ref, factor_gen], "0 < min <= max")
    if factor_gen[1] > factor_ref[0]:
        raise _fail(
            "precios.factor_generico", list(factor_gen), "máximo genérico <= mínimo de referencia"
        )
    pl = _table(data, "precios.piezas_lognormal")
    sigma = _number(pl["sigma"], "precios.piezas_lognormal.sigma")
    if sigma <= 0:
        raise _fail("precios.piezas_lognormal.sigma", sigma, "> 0")
    precios = Precios(
        nivel=rangos,
        factor_referencia=factor_ref,
        factor_generico=factor_gen,
        ruido_max=_in_range(
            pre["ruido_max"], "precios.ruido_max", 0, 0.5, "[0, 0.5)", high_open=True
        ),
        piezas_mu=_number(pl["mu"], "precios.piezas_lognormal.mu"),
        piezas_sigma=sigma,
    )

    _table(data, "patrones")
    p5_tab = _table(data, "patrones.p5")
    p5_moleculas = p5_tab["moleculas"]
    if not isinstance(p5_moleculas, list) or not p5_moleculas:
        raise ConfigError("patrones.p5.moleculas: debe ser una lista no vacía")
    for name in p5_moleculas:
        if name not in moleculas:
            raise ConfigError(
                f"patrones.p5.moleculas: {name!r} no existe en reference/moleculas.csv"
            )
        if name not in destacadas:
            raise ConfigError(
                f"patrones.p5.moleculas: {name!r} debe estar en concentracion.moleculas_destacadas"
            )
    inicial = _in_range(
        p5_tab["cuota_generico_inicial"], "patrones.p5.cuota_generico_inicial", 0, 1, "[0, 1]"
    )
    final = _in_range(
        p5_tab["cuota_generico_final"], "patrones.p5.cuota_generico_final", 0, 1, "[0, 1]"
    )
    if inicial >= final:
        raise _fail("patrones.p5", [inicial, final], "cuota inicial < cuota final")
    p5 = PatronP5(tuple(p5_moleculas), inicial, final)

    p3_tab = _table(data, "patrones.p3")
    ejemplo = p3_tab["molecula_ejemplo"]
    if ejemplo not in moleculas:
        raise ConfigError(
            f"patrones.p3.molecula_ejemplo: {ejemplo!r} no existe en reference/moleculas.csv"
        )
    if ejemplo in p5.moleculas:
        raise ConfigError(
            f"patrones.p3.molecula_ejemplo: {ejemplo!r} no puede estar en patrones.p5.moleculas"
        )
    if ejemplo not in destacadas:
        raise ConfigError(
            f"patrones.p3.molecula_ejemplo: {ejemplo!r} debe estar en "
            "concentracion.moleculas_destacadas"
        )
    prob = _mapping(p3_tab["prob_referencia"], "patrones.p3.prob_referencia", instituciones)
    for name, value in prob.items():
        _in_range(value, f"patrones.p3.prob_referencia.{name}", 0, 1, "[0, 1]")
    p3 = PatronP3(ejemplo, {k: float(prob[k]) for k in instituciones})

    p4_tab = _table(data, "patrones.p4")
    factor_2025 = p4_tab["factor_2025"]
    if not isinstance(factor_2025, dict):
        raise ConfigError("patrones.p4.factor_2025: debe ser una tabla")
    for name, value in factor_2025.items():
        if name not in grupos:
            raise ConfigError(f"patrones.p4.factor_2025.{name}: grupo terapéutico que no existe")
        if _number(value, f"patrones.p4.factor_2025.{name}") <= 0:
            raise _fail(f"patrones.p4.factor_2025.{name}", value, "> 0")
    resto = _number(p4_tab["factor_2025_resto"], "patrones.p4.factor_2025_resto")
    if resto <= 0:
        raise _fail("patrones.p4.factor_2025_resto", resto, "> 0")
    p4 = PatronP4({k: float(v) for k, v in factor_2025.items()}, resto)

    return Config(
        seed, periodo, volumen, huerfanos, concentracion, estacionalidad, precios, p3, p4, p5, raw
    )
