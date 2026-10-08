"""Command line: python -m warehouse {schema,load,checks,checks-negativos}."""

from __future__ import annotations

import argparse

from warehouse import commands

_COMMANDS = {
    "schema": (commands.run_schema, "crea el dataset y las tablas desde sql/farma_analytics.sql"),
    "load": (commands.run_load, "verifica data/, carga los CSV y ejecuta los chequeos"),
    "checks": (commands.run_checks, "verifica los metadatos y ejecuta los chequeos de calidad"),
    "checks-negativos": (
        commands.run_negative_checks_command,
        "comprueba que cada chequeo detecta su caso negativo",
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m warehouse",
        description="Esquema, carga y chequeos de calidad de farma_analytics en BigQuery.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="comando")
    for name, (_, help_text) in _COMMANDS.items():
        sub.add_parser(name, help=help_text)
    args = parser.parse_args(argv)
    return _COMMANDS[args.command][0]()


if __name__ == "__main__":
    raise SystemExit(main())
