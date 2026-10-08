"""Command line: python -m warehouse {schema,vista,load,checks,checks-negativos,consultas}."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from warehouse import commands

# Subcommand -> function that runs it and returns the exit code.
_COMMANDS: dict[str, Callable[[], int]] = {
    "schema": commands.run_schema,
    "vista": commands.run_view,
    "load": commands.run_load,
    "checks": commands.run_checks,
    "checks-negativos": commands.run_negative_checks_command,
    "consultas": commands.run_queries,
}

# Subcommand -> help text shown by --help.
_HELP = {
    "schema": "crea el dataset farma_analytics y las tablas COMPRAS, CLUE_CAT y CUADRO_BASICO",
    "vista": "crea o reemplaza la vista v_compras_farma_completa y ejecuta los chequeos",
    "load": "verifica data/, carga los CSV en las tres tablas y ejecuta los chequeos",
    "checks": "compara los metadatos con la DDL y ejecuta los chequeos de calidad",
    "checks-negativos": "comprueba que cada chequeo detecta el error de su caso negativo",
    "consultas": "responde las tres preguntas comerciales sobre la vista y cruza sus cifras",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m warehouse",
        description="Esquema, vista, carga, chequeos y consultas de farma_analytics en BigQuery.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="comando")
    for name in _COMMANDS:
        sub.add_parser(name, help=_HELP[name])
    args = parser.parse_args(argv)
    return _COMMANDS[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
