"""End-to-end generation of the three sources and the manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from faker import Faker

from generator.config import load_config
from generator.manifest import build_manifest, dumps, file_entry
from generator.purchases import build_purchases
from generator.reference import load_reference
from generator.rng import make_streams
from generator.supplies import build_supplies
from generator.units import build_units
from generator.writer import MANIFEST_NAME, format_importe, staging, write_csv

HEADERS = {
    "COMPRAS": [
        "CLUE",
        "CLAVE",
        "COD_PROVEEDOR",
        "MARCA",
        "FABRICANTE",
        "PIEZAS",
        "IMPORTE",
        "FECHA",
    ],
    "CLUE_CAT": [
        "CLUE",
        "ENTIDAD",
        "INSTITUCION",
        "DELEGACION",
        "GRUPO_INSTITUCIONAL",
        "NIVEL_ATENCION",
        "MUNICIPIO",
    ],
    "CUADRO_BASICO": [
        "CLAVE",
        "DESCRIPCION",
        "MOLECULA",
        "GRUPO_TERAPEUTICO",
        "PRESENTACION",
        "FABRICANTE",
    ],
}


def generate(config_path: Path, out_dir: Path) -> dict[str, Any]:
    """Validate the configuration, build the data and replace the outputs atomically."""
    reference = load_reference()
    config = load_config(Path(config_path), reference)
    streams = make_streams(config.seed)
    faker = Faker("es_MX")
    faker.seed_instance(streams.faker_seed)

    units = build_units(config, reference, streams.units)
    supplies = build_supplies(config, reference, streams.supplies, streams.companies, faker)
    purchases = build_purchases(config, units, supplies, streams.purchases, streams.orphans)

    with staging(Path(out_dir)) as tmp:
        write_csv(
            tmp / "CLUE_CAT.csv",
            HEADERS["CLUE_CAT"],
            (
                (
                    u.clue,
                    u.entidad,
                    u.institucion,
                    u.delegacion,
                    u.grupo_institucional,
                    u.nivel_atencion,
                    u.municipio,
                )
                for u in units
            ),
        )
        write_csv(
            tmp / "CUADRO_BASICO.csv",
            HEADERS["CUADRO_BASICO"],
            (
                (
                    c.clave,
                    c.descripcion,
                    c.molecula,
                    c.grupo_terapeutico,
                    c.presentacion,
                    c.fabricante,
                )
                for c in supplies.claves
            ),
        )
        write_csv(
            tmp / "COMPRAS.csv",
            HEADERS["COMPRAS"],
            (
                (clue, clave, prov, marca, fab, str(pz), format_importe(importe), fecha.isoformat())
                for clue, clave, prov, marca, fab, pz, importe, fecha in purchases.rows
            ),
        )
        files = [file_entry(tmp / f"{name}.csv") for name in HEADERS]
        manifest = build_manifest(config.raw, files, purchases.orphans)
        (tmp / MANIFEST_NAME).write_text(dumps(manifest), encoding="utf-8", newline="\n")
    return manifest
