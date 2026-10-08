"""Shared fixtures for the synthetic data generator tests."""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "generator" / "config.toml"
SMALL_CONFIG = REPO_ROOT / "tests" / "generator" / "fixtures" / "config_small.toml"
CSV_NAMES = ("CLUE_CAT.csv", "COMPRAS.csv", "CUADRO_BASICO.csv")


def run_generator(
    *args: str, cwd: Path = REPO_ROOT, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run `python -m generator` and return the completed process."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "generator", *args],
        cwd=cwd,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Header and rows of a generated CSV."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


@pytest.fixture(scope="session")
def full_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Default configuration generated once per session."""
    out = tmp_path_factory.mktemp("full")
    proc = run_generator("generate", "--config", str(DEFAULT_CONFIG), "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    return out


@pytest.fixture(scope="session")
def full_tables(full_dataset: Path) -> dict[str, list[dict[str, str]]]:
    """Rows of the three tables of the full dataset, keyed by table name."""
    return {name.removesuffix(".csv"): read_csv(full_dataset / name)[1] for name in CSV_NAMES}


@pytest.fixture
def small_config() -> Path:
    return SMALL_CONFIG


@pytest.fixture
def run_gen():
    """The run_generator helper, exposed as a fixture (importlib mode)."""
    return run_generator


@pytest.fixture
def read_table():
    """The read_csv helper, exposed as a fixture (importlib mode)."""
    return read_csv


@pytest.fixture
def default_config() -> Path:
    return DEFAULT_CONFIG


@pytest.fixture(scope="session")
def full_model():
    """Reference, config and supplies rebuilt in-process for the default configuration."""
    from faker import Faker

    from generator.config import load_config
    from generator.reference import load_reference
    from generator.rng import make_streams
    from generator.supplies import build_supplies

    reference = load_reference()
    config = load_config(DEFAULT_CONFIG, reference)
    streams = make_streams(config.seed)
    faker = Faker("es_MX")
    faker.seed_instance(streams.faker_seed)
    supplies = build_supplies(config, reference, streams.supplies, streams.companies, faker)
    return {"reference": reference, "config": config, "supplies": supplies}
