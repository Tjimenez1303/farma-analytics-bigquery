"""Command line: python -m warehouse <comando>, one subcommand per BigQuery target of the Makefile."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from warehouse import commands, dashboard

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
    "dashboard": "calcula sobre la vista las cifras del dashboard con los filtros indicados",
}

# Option of the dashboard subcommand for each list control.
_LIST_OPTIONS = {
    "entidades": "--entidad",
    "instituciones": "--institucion",
    "grupos_institucionales": "--grupo-institucional",
    "grupos_terapeuticos": "--grupo-terapeutico",
    "moleculas": "--molecula",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m warehouse",
        description=(
            "Esquema, vista, carga, chequeos, consultas y cifras del dashboard de farma_analytics "
            "en BigQuery."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="comando")
    for name in _COMMANDS:
        sub.add_parser(name, help=_HELP[name])
    _add_dashboard(sub)
    args = parser.parse_args(argv)
    if args.command == "dashboard":
        return _run_dashboard(args)
    return _COMMANDS[args.command]()


def _add_dashboard(sub) -> None:
    board = sub.add_parser("dashboard", help=_HELP["dashboard"])
    start, end = dashboard.DEFAULT_START.isoformat(), dashboard.DEFAULT_END.isoformat()
    board.set_defaults(desde=start, hasta=end)
    dates = {
        "--desde": f"inicio del control Periodo ({start})",
        "--hasta": f"fin del control Periodo ({end})",
    }
    for option, help_text in dates.items():
        board.add_argument(option, metavar="AAAA-MM-DD", help=help_text)
    for name, option in _LIST_OPTIONS.items():
        help_text = f"valores del control {dashboard.LISTS[name]}, separados por comas"
        board.add_argument(option, dest=name, metavar="VALORES", help=help_text)


def _run_dashboard(args: argparse.Namespace) -> int:
    lists = {name: getattr(args, name) for name in _LIST_OPTIONS}
    try:
        filters = dashboard.build_filters(args.desde, args.hasta, **lists)
    except dashboard.FilterError as exc:
        print(exc, file=sys.stderr)
        return 2
    return commands.run_dashboard(filters)


if __name__ == "__main__":
    raise SystemExit(main())
