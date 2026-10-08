"""bq command builders and the single entry point that runs them."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = "farma_analytics"
TIMEOUT_SECONDS = 600

_ESTIMATED_BYTES = re.compile(r"will process (\d+) bytes")


class BqEnvironmentError(Exception):
    """Invalid environment for bq; the CLI maps it to exit code 2."""


@dataclass(frozen=True)
class Command:
    """bq arguments plus the SQL sent on stdin, if any."""

    argv: tuple[str, ...]
    stdin: str | None = None


@dataclass(frozen=True)
class BqResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def output(self) -> str:
        """stdout and stderr together, since bq prints errors on either."""
        return "\n".join(part for part in (self.stdout.strip(), self.stderr.strip()) if part)


def check_environment() -> None:
    """Fail early when bq would not use the repository defaults or the project."""
    expected = REPO_ROOT / ".bigqueryrc"
    rc = os.environ.get("BIGQUERYRC", "")
    if not rc or not Path(rc).is_file() or not Path(rc).samefile(expected):
        raise BqEnvironmentError(
            f"BIGQUERYRC debe apuntar a {expected}. Ejecuta el comando con make."
        )
    if not os.environ.get("PROJECT_ID"):
        raise BqEnvironmentError(
            "Falta PROJECT_ID: define GOOGLE_CLOUD_PROJECT en .env o ejecuta "
            "gcloud config set project <PROJECT_ID>, y usa make."
        )
    job_labels()
    if shutil.which("bq") is None:
        raise BqEnvironmentError(
            "No se encuentra bq en el PATH. Revisa la instalación con make doctor."
        )


def job_labels() -> list[str]:
    """Query job labels from BQ_JOB_LABELS, which the Makefile fills from BQ_LABELS."""
    labels = shlex.split(os.environ.get("BQ_JOB_LABELS", ""))
    if not labels or any(not label.startswith("--label=") for label in labels):
        raise BqEnvironmentError(
            "BQ_JOB_LABELS debe contener las labels de los jobs (--label=clave:valor). Usa make."
        )
    return labels


def _base(as_json: bool = False) -> list[str]:
    argv = ["bq", f"--project_id={os.environ.get('PROJECT_ID', '')}"]
    if as_json:
        argv.append("--format=json")
    return argv


def dry_run_query(sql: str, params: Sequence[str] = ()) -> Command:
    """Dry run of a query job; the SQL goes on stdin so leading comments are not read as flags."""
    return Command((*_base(), "query", "--dry_run", *params), stdin=sql)


def run_query(
    sql: str,
    params: Sequence[str] = (),
    *,
    as_json: bool = False,
    max_rows: int | None = None,
) -> Command:
    """Labeled query job; dialect, location and byte limit come from .bigqueryrc."""
    argv = [*_base(as_json), "query", *job_labels()]
    if max_rows is not None:
        argv.append(f"--max_rows={max_rows}")
    return Command((*argv, *params), stdin=sql)


def load_csv(table_ref: str, csv_path: Path, schema_path: Path) -> Command:
    """Atomic replacement of a table from a local CSV with an explicit schema."""
    return Command(
        (
            *_base(),
            "load",
            "--replace",
            "--source_format=CSV",
            "--skip_leading_rows=1",
            "--autodetect=false",
            "--max_bad_records=0",
            "--encoding=UTF-8",
            table_ref,
            str(csv_path),
            str(schema_path),
        )
    )


def show(ref: str) -> Command:
    """Metadata read of a dataset or table (no job)."""
    return Command((*_base(as_json=True), "show", ref))


def estimated_bytes(output: str) -> int | None:
    """Bytes reported by a dry run, or None when the message does not include them."""
    match = _ESTIMATED_BYTES.search(output)
    return int(match.group(1)) if match else None


def execute(command: Command) -> BqResult:
    """Run bq without a shell; the only subprocess call of the package."""
    try:
        proc = subprocess.run(
            list(command.argv),
            input=command.stdin,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return BqResult(124, "", f"bq no respondió en {TIMEOUT_SECONDS} s.")
    except FileNotFoundError:
        return BqResult(127, "", "No se encuentra bq en el PATH.")
    return BqResult(proc.returncode, proc.stdout, proc.stderr)
