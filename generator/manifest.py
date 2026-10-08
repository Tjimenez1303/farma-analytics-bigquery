"""SHA-256 manifest of the generated files and its verification."""

from __future__ import annotations

import hashlib
import json
import platform
from importlib import metadata
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1


def file_entry(path: Path) -> dict[str, Any]:
    """Name, SHA-256, size and data rows (header excluded) of one CSV."""
    path = Path(path)
    with open(path, "rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    with open(path, "rb") as f:
        lines = sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 20), b""))
    return {
        "bytes": path.stat().st_size,
        "name": path.name,
        "rows": max(lines - 1, 0),
        "sha256": digest,
    }


def runtime_versions() -> dict[str, str]:
    """Exact Python, NumPy and Faker versions in use."""
    return {
        "faker": metadata.version("faker"),
        "numpy": metadata.version("numpy"),
        "python": platform.python_version(),
    }


def build_manifest(
    config_bytes: bytes, files: list[dict[str, Any]], orphans: dict[str, int]
) -> dict[str, Any]:
    return {
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "files": sorted(files, key=lambda f: f["name"]),
        "format_version": FORMAT_VERSION,
        "orphans": {"CLAVE": int(orphans["CLAVE"]), "CLUE": int(orphans["CLUE"])},
        "versions": runtime_versions(),
    }


def dumps(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def load(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """One line in Spanish per difference; empty when both manifests match."""
    diffs: list[str] = []
    actual_files = {f["name"]: f for f in actual.get("files", [])}
    for exp in expected.get("files", []):
        name = exp["name"]
        got = actual_files.get(name)
        if got is None:
            diffs.append(f"{name}: falta el archivo")
            continue
        for key in ("sha256", "bytes", "rows"):
            if exp[key] != got[key]:
                diffs.append(f"{name}: {key} esperado {exp[key]}, obtenido {got[key]}")
    for key in ("config_sha256", "orphans"):
        if expected.get(key) != actual.get(key):
            diffs.append(f"{key}: esperado {expected.get(key)}, obtenido {actual.get(key)}")
    if diffs and expected.get("versions") != actual.get("versions"):
        diffs.append(
            f"versiones distintas: esperado {expected.get('versions')}, "
            f"obtenido {actual.get('versions')}"
        )
    return diffs


def verify(expected_path: Path, data_dir: Path) -> tuple[list[str], list[str]]:
    """Recompute the files listed in the expected manifest; returns (ok lines, diff lines)."""
    expected = load(expected_path)
    data_dir = Path(data_dir)
    generated_path = data_dir / "manifest.json"
    generated = load(generated_path) if generated_path.exists() else {}
    files = [
        file_entry(data_dir / f["name"])
        for f in expected["files"]
        if (data_dir / f["name"]).exists()
    ]
    actual = {
        "config_sha256": generated.get("config_sha256"),
        "files": files,
        "orphans": generated.get("orphans"),
        "versions": generated.get("versions", runtime_versions()),
    }
    diffs = compare(expected, actual)
    if not generated_path.exists():
        diffs.insert(0, f"{generated_path}: falta el manifiesto generado")
    bad = {d.split(":", 1)[0] for d in diffs}
    ok = [f"{f['name']}: OK" for f in expected["files"] if f["name"] not in bad]
    return ok, diffs
