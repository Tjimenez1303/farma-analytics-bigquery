"""Tests that the repository .sqlfluff accepts the style reference and rejects each violation."""

import json
import shutil
import subprocess
import sys

import pytest

EXPECTED_CODES = {"CP01", "AL01", "AM05", "ST07", "AM06", "CV03", "LT05", "AL06", "LT03"}


def lint(repo_root, tmp_path, name):
    """Lint a fixture copied next to the repository config (fixtures are sqlfluff-ignored)."""
    shutil.copy(repo_root / ".sqlfluff", tmp_path / ".sqlfluff")
    target = tmp_path / name
    shutil.copy(repo_root / "tests" / "fixtures" / "sql" / name, target)
    proc = subprocess.run(
        [sys.executable, "-m", "sqlfluff", "lint", "--format", "json", str(target)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    report = json.loads(proc.stdout)
    return {v["code"] for item in report for v in item["violations"]}, report


def test_style_reference_passes(repo_root, tmp_path):
    codes, report = lint(repo_root, tmp_path, "conforme.sql")
    assert codes == set(), report


@pytest.mark.parametrize("code", sorted(EXPECTED_CODES))
def test_each_violation_is_detected(repo_root, tmp_path, code):
    codes, report = lint(repo_root, tmp_path, "no_conforme.sql")
    assert "PRS" not in codes, report
    assert code in codes, sorted(codes)
