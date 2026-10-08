"""Command line: python -m generator generate | verify."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generator.config import ConfigError
from generator.reference import ReferenceError


def _generate(args: argparse.Namespace) -> int:
    from generator.pipeline import generate

    try:
        manifest = generate(Path(args.config), Path(args.out))
    except (ConfigError, ReferenceError) as exc:
        print(f"Configuración inválida: {exc}", file=sys.stderr)
        return 2
    for entry in manifest["files"]:
        print(f"{entry['name']}: {entry['rows']} filas, sha256 {entry['sha256'][:12]}")
    orphans = manifest["orphans"]
    print(f"Huérfanos: CLUE {orphans['CLUE']}, CLAVE {orphans['CLAVE']}")
    return 0


def _verify(args: argparse.Namespace) -> int:
    from generator.manifest import verify

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Falta el manifiesto de referencia {manifest_path}.", file=sys.stderr)
        return 1
    ok, diffs = verify(manifest_path, Path(args.data))
    for line in ok:
        print(line)
    for line in diffs:
        print(f"DIFIERE {line}")
    if diffs:
        print("Los archivos no coinciden con el manifiesto de referencia.", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator", description="Generador de datos sintéticos."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Genera los tres CSV y el manifiesto.")
    gen.add_argument("--config", default="generator/config.toml")
    gen.add_argument("--out", default="data")
    gen.set_defaults(func=_generate)
    ver = sub.add_parser("verify", help="Compara data/ con el manifiesto de referencia.")
    ver.add_argument("--manifest", default="generator/manifest.json")
    ver.add_argument("--data", default="data")
    ver.set_defaults(func=_verify)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
