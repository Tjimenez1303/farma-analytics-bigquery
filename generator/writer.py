"""CSV writing and atomic replacement of the output files."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

MANIFEST_NAME = "manifest.json"


def format_importe(centavos: int) -> str:
    """Integer cents as pesos with exactly two decimals."""
    return f"{centavos // 100}.{centavos % 100:02d}"


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    """UTF-8 without BOM, LF line endings, minimal quoting."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        writer.writerows(rows)


@contextmanager
def staging(out_dir: Path) -> Iterator[Path]:
    """Temporary directory inside out_dir whose files replace the outputs on success."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=out_dir))
    try:
        yield tmp
        names = sorted(p.name for p in tmp.iterdir() if p.name != MANIFEST_NAME)
        for name in names:
            os.replace(tmp / name, out_dir / name)
        if (tmp / MANIFEST_NAME).exists():
            os.replace(tmp / MANIFEST_NAME, out_dir / MANIFEST_NAME)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
