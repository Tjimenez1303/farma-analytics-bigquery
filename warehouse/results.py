"""Common result row of the SQL checks and the metadata verification."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import astuple, dataclass

COLUMNS = ("CHEQUEO", "OBJETO", "DETALLE", "ESPERADO", "OBTENIDO")


@dataclass(frozen=True)
class CheckResult:
    chequeo: str
    objeto: str
    detalle: str
    esperado: str
    obtenido: str


def from_row(row: Mapping[str, object]) -> CheckResult:
    """CheckResult from one JSON row returned by bq. NULL values become 'NULL'."""
    values = ["NULL" if row.get(column) is None else str(row[column]) for column in COLUMNS]
    return CheckResult(*values)


def format_table(results: Iterable[CheckResult]) -> str:
    """Left-aligned text table with a header row."""
    rows = [COLUMNS, *(astuple(result) for result in results)]
    widths = [max(len(row[i]) for row in rows) for i in range(len(COLUMNS))]
    return "\n".join(
        "  ".join(value.ljust(width) for value, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    )
