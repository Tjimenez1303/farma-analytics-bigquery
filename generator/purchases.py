"""COMPRAS: purchase lines with prices derived from base price, manufacturer and noise."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np

from generator.config import Config
from generator.supplies import ESPECIFICO_MAX, ESPECIFICO_MIN, Supplies
from generator.units import CONSECUTIVO_MAX, Unit


@dataclass(frozen=True)
class Purchases:
    rows: list[tuple[str, str, str, str, str, int, int, dt.date]]
    orphans: dict[str, int]


def period_days(config: Config) -> list[dt.date]:
    """Every day of the period, only weekdays when configured."""
    days = []
    day = config.periodo.inicio
    while day <= config.periodo.fin:
        if not config.periodo.solo_dias_laborables or day.weekday() < 5:
            days.append(day)
        day += dt.timedelta(days=1)
    return days


def _dates(config: Config, rng: np.random.Generator) -> list[dt.date]:
    """Line dates: monthly multinomial with seasonality and growth, uniform inside the month."""
    months: dict[tuple[int, int], list[dt.date]] = {}
    for day in period_days(config):
        months.setdefault((day.year, day.month), []).append(day)
    keys = sorted(months)
    first_year = config.periodo.inicio.year
    est = config.estacionalidad
    weights = np.array(
        [est.factores_mes[m - 1] * (1 + est.crecimiento_total) ** (y - first_year) for y, m in keys]
    )
    counts = rng.multinomial(config.volumen.lineas_compra, weights / weights.sum())
    dates: list[dt.date] = []
    for key, count in zip(keys, counts, strict=True):
        pool = months[key]
        picks = rng.integers(0, len(pool), size=int(count))
        dates.extend(pool[i] for i in picks)
    return dates


def molecule_ranks(config: Config, supplies: Supplies, rng: np.random.Generator) -> dict[str, int]:
    """Zipf rank of each molecule: fixed for highlighted ones, random for the rest."""
    moleculas = sorted(supplies.autorizados)
    fixed = config.concentracion.moleculas_destacadas
    free_ranks = [r for r in range(1, len(moleculas) + 1) if r not in set(fixed.values())]
    free_mols = [m for m in moleculas if m not in fixed]
    order = rng.permutation(len(free_mols))
    ranks = dict(fixed)
    for rank, idx in zip(free_ranks, order, strict=True):
        ranks[free_mols[int(idx)]] = rank
    return ranks


def molecule_weights(
    config: Config, supplies: Supplies, ranks: dict[str, int], year: int, grupos: dict[str, str]
) -> np.ndarray:
    """Zipf weights by molecule (sorted by name) for one year."""
    moleculas = sorted(supplies.autorizados)
    w = np.array([1.0 / ranks[m] ** config.concentracion.alpha_moleculas for m in moleculas])
    if year == config.periodo.fin.year:
        p4 = config.p4
        w = w * np.array([p4.factor_2025.get(grupos[m], p4.factor_2025_resto) for m in moleculas])
    return w / w.sum()


def _unit_probabilities(config: Config, units: tuple[Unit, ...]) -> np.ndarray:
    """Institution share times care-level weight, normalized inside each institution."""
    con = config.concentracion
    level_w = np.array([con.peso_compra_nivel[u.nivel_atencion] for u in units])
    inst = np.array([u.institucion for u in units])
    p = np.zeros(len(units))
    for name, share in con.participacion_institucion.items():
        mask = inst == name
        p[mask] = share * level_w[mask] / level_w[mask].sum()
    return p / p.sum()


def p5_generics(config: Config, supplies: Supplies, rng: np.random.Generator) -> dict[str, str]:
    """Generic manufacturer that gains share in each P5 molecule."""
    chosen = {}
    for molecula in config.p5.moleculas:
        generics = supplies.autorizados[molecula][1:]
        chosen[molecula] = generics[int(rng.integers(0, len(generics)))]
    return chosen


def p5_share(config: Config, year: int) -> float:
    """Chosen generic share: initial in the first year, final in the last, linear in between."""
    first, last = config.periodo.inicio.year, config.periodo.fin.year
    t = (year - first) / (last - first)
    return config.p5.cuota_generico_inicial + t * (
        config.p5.cuota_generico_final - config.p5.cuota_generico_inicial
    )


def manufacturer_probabilities(
    config: Config,
    supplies: Supplies,
    molecula: str,
    institucion: str,
    year: int,
    chosen: dict[str, str],
) -> list[tuple[str, float]]:
    """P3 reference share by institution. In P5 molecules the chosen generic share comes first."""
    reference, *generics = supplies.autorizados[molecula]
    p_ref = config.p3.prob_referencia[institucion]
    if molecula in chosen:
        target = chosen[molecula]
        c = p5_share(config, year)
        others = [g for g in generics if g != target]
        if not others:
            return [(reference, 1 - c), (target, c)]
        rest = (1 - c) * (1 - p_ref) / len(others)
        return [(reference, (1 - c) * p_ref), (target, c)] + [(g, rest) for g in others]
    return [(reference, p_ref)] + [(g, (1 - p_ref) / len(generics)) for g in generics]


def choose_manufacturer(probabilities: list[tuple[str, float]], u: float) -> str:
    """Inverse-CDF pick with a uniform draw."""
    acc = 0.0
    for name, p in probabilities:
        acc += p
        if u < acc:
            return name
    return probabilities[-1][0]


def inject_orphans(
    config: Config,
    rows: list,
    units: tuple[Unit, ...],
    supplies: Supplies,
    rng: np.random.Generator,
) -> dict[str, int]:
    """Replace the CLUE or CLAVE of exactly round(orphan_rate x rows) lines with unused keys."""
    n = len(rows)
    total = round(config.huerfanos.orphan_rate * n)
    if total == 0:
        return {"CLAVE": 0, "CLUE": 0}
    n_clue = round(total * config.huerfanos.proporcion_clue)
    picked = rng.choice(n, size=total, replace=False)
    used_clues = {u.clue for u in units}
    free_esp = sorted(set(range(ESPECIFICO_MIN, ESPECIFICO_MAX + 1)) - supplies.especificos_usados)
    for k, i in enumerate(picked):
        clue, clave, *rest = rows[int(i)]
        if k < n_clue:
            while True:
                candidate = f"{clue[:5]}{int(rng.integers(1, CONSECUTIVO_MAX + 1)):06d}"
                if candidate not in used_clues:
                    break
            rows[int(i)] = (candidate, clave, *rest)
        else:
            esp = free_esp[int(rng.integers(0, len(free_esp)))]
            rows[int(i)] = (clue, f"010.000.{esp:04d}.00", *rest)
    return {"CLAVE": total - n_clue, "CLUE": n_clue}


def build_purchases(
    config: Config,
    units: tuple[Unit, ...],
    supplies: Supplies,
    rng: np.random.Generator,
    orphan_rng: np.random.Generator,
) -> Purchases:
    n = config.volumen.lineas_compra
    dates = _dates(config, rng)
    years = np.array([d.year for d in dates])
    unit_idx = rng.choice(len(units), size=n, p=_unit_probabilities(config, units))

    moleculas = sorted(supplies.autorizados)
    grupos = {c.molecula: c.grupo_terapeutico for c in supplies.claves}
    ranks = molecule_ranks(config, supplies, rng)
    mol_idx = np.empty(n, dtype=np.int64)
    for year in sorted(set(years.tolist())):
        mask = years == year
        p = molecule_weights(config, supplies, ranks, year, grupos)
        mol_idx[mask] = rng.choice(len(moleculas), size=int(mask.sum()), p=p)

    chosen = p5_generics(config, supplies, rng)
    cache: dict[tuple[str, str, int], list[tuple[str, float]]] = {}
    claves_by_mol: dict[str, list] = {}
    for c in supplies.claves:
        claves_by_mol.setdefault(c.molecula, []).append(c)
    u_clave = rng.random(n)
    u_fab = rng.random(n)
    u_prov = rng.random(n)
    pre = config.precios
    piezas = np.clip(
        np.rint(rng.lognormal(pre.piezas_mu, pre.piezas_sigma, size=n)),
        1,
        config.volumen.piezas_max,
    ).astype(np.int64)
    noise = rng.uniform(1 - pre.ruido_max, 1 + pre.ruido_max, size=n)

    rows = []
    for i in range(n):
        unit = units[int(unit_idx[i])]
        molecula = moleculas[int(mol_idx[i])]
        options = claves_by_mol[molecula]
        clave = options[min(int(u_clave[i] * len(options)), len(options) - 1)]
        key = (molecula, unit.institucion, int(years[i]))
        if key not in cache:
            cache[key] = manufacturer_probabilities(config, supplies, *key, chosen)
        fab = choose_manufacturer(cache[key], float(u_fab[i]))
        provs = supplies.proveedores[fab]
        prov = provs[min(int(u_prov[i] * len(provs)), len(provs) - 1)]
        precio = int(np.rint(clave.base_centavos * supplies.fabricantes[fab].factor * noise[i]))
        pz = int(piezas[i])
        rows.append(
            (
                unit.clue,
                clave.clave,
                prov,
                supplies.marcas[(fab, molecula)],
                fab,
                pz,
                pz * precio,
                dates[i],
            )
        )

    orphans = inject_orphans(config, rows, units, supplies, orphan_rng)
    order = sorted(range(n), key=lambda i: (rows[i][7], rows[i][0], rows[i][1], i))
    return Purchases(rows=[rows[i] for i in order], orphans=orphans)
