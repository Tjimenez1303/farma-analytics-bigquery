"""Rules of contracts/especificacion-dashboard.md on docs/dashboard.md, the written dashboard spec."""

import csv
import os
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from warehouse.ddl import parse_file

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "dashboard.md"
ENTITIES = ROOT / "generator" / "reference" / "entidades.csv"
FIELDS_HEADER = "| Columna | Nombre de negocio | Tipo | Agregación | Uso |"
FORMULAS_HEADER = "| Campo calculado | Fórmula | Tipo | Agregación | Uso |"
CONTRAST_HEADER = "| Primer plano | Fondo | Uso | Contraste | Umbral |"
SIZES_HEADER = "| Tamaño de letra | Uso |"
ABBREVIATIONS_HEADER = "| Clave INEGI | Entidad | Abreviatura |"
# Room Data Studio leaves for each name in a horizontal bar chart, measured in the product.
MAX_ABBREVIATION = 6
HEX = re.compile(r"`(#[0-9A-Fa-f]{6})`")


@pytest.fixture(scope="module")
def text() -> str:
    return SPEC.read_text(encoding="utf-8")


def _table(text: str, header: str) -> list[list[str]]:
    """Cells of the Markdown table that starts with header, without the separator row."""
    lines = text.splitlines()
    start = lines.index(header)
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def _luminance(hex_color: str) -> float:
    """Relative luminance of WCAG 2.1."""
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> Decimal:
    """WCAG 2.1 contrast ratio of two colors, rounded to two decimals."""
    light, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    ratio = Decimal(str((light + 0.05) / (dark + 0.05)))
    return ratio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def test_contrast_formula_matches_known_pairs():
    assert contrast("#000000", "#FFFFFF") == Decimal("21.00")
    assert contrast("#0072B2", "#FFFFFF") == Decimal("5.19")


def test_fields_table_covers_exactly_the_view_columns(text):
    view = parse_file().view
    names = [row[0].strip("`") for row in _table(text, FIELDS_HEADER)]
    assert names == [column.name for column in view.columns]


def test_no_average_in_calculated_fields(text):
    formulas = [row[1] for row in _table(text, FORMULAS_HEADER)]
    assert formulas
    assert all("AVG" not in formula.upper() for formula in formulas)


def test_declared_contrasts_match_wcag_and_pass(text):
    rows = _table(text, CONTRAST_HEADER)
    assert rows
    for foreground, background, use, declared, threshold in rows:
        if threshold == "No aplica":
            continue
        pair = [HEX.search(foreground).group(1), HEX.search(background).group(1)]
        measured = contrast(*pair)
        assert declared == f"{measured}:1", use
        assert measured >= Decimal(threshold.removesuffix(":1")), use


def test_abbreviations_cover_the_catalog_entities(text):
    rows = _table(text, ABBREVIATIONS_HEADER)
    with ENTITIES.open(encoding="utf-8") as handle:
        catalog = [(row["cve_ent"], row["entidad"]) for row in csv.DictReader(handle)]
    assert [(key, name) for key, name, _ in rows] == catalog
    abbreviations = [abbreviation for _, _, abbreviation in rows]
    assert len(set(abbreviations)) == len(abbreviations)
    assert all(len(abbreviation) <= MAX_ABBREVIATION for abbreviation in abbreviations)


def test_three_font_sizes_or_fewer(text):
    sizes = _table(text, SIZES_HEADER)
    assert 1 <= len(sizes) <= 3


def test_no_project_id(text):
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        assert project not in text
