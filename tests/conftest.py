"""Shared fixtures for the repository script tests."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STUBS_DIR = REPO_ROOT / "tests" / "fixtures" / "stubs"
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


@pytest.fixture
def repo_root():
    """Absolute path of the repository."""
    return REPO_ROOT


@pytest.fixture
def run_script():
    """Run a command and return the completed process with text output."""

    def _run(args, env=None, input=None, cwd=REPO_ROOT):
        base = {
            "HOME": os.environ.get("HOME", ""),
            "PATH": os.environ.get("PATH", SYSTEM_PATH),
            "LC_ALL": "C.UTF-8",
        }
        if env:
            base.update(env)
        return subprocess.run(
            [str(a) for a in args],
            env=base,
            input=input,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    return _run


def system_path_without(names, root):
    """SYSTEM_PATH, or a symlink copy of its executables minus names when any of them lives there."""
    if not any(shutil.which(name, path=SYSTEM_PATH) for name in names):
        return SYSTEM_PATH
    sysbin = root / "sysbin"
    sysbin.mkdir()
    for directory in SYSTEM_PATH.split(":"):
        if not os.path.isdir(directory):
            continue
        for entry in sorted(Path(directory).iterdir()):
            link = sysbin / entry.name
            if entry.name in names or link.is_symlink() or link.exists():
                continue
            link.symlink_to(entry)
    return str(sysbin)


@pytest.fixture
def stub_path(tmp_path):
    """Copy the stubs to a temp dir and return an env dict that puts them first in PATH."""

    def _build(overrides=None, remove=()):
        stubs = tmp_path / "stubs"
        shutil.copytree(STUBS_DIR, stubs)
        for name in remove:
            (stubs / "bin" / name).unlink()
        env = {
            "PATH": f"{stubs / 'bin'}:{system_path_without(remove, tmp_path)}",
            "STUB_LOG": str(tmp_path / "stub.log"),
            "REAL_PYTHON": sys.executable,
            "DOCTOR_VENV": str(stubs / "venv"),
        }
        if overrides:
            env.update(overrides)
        return env

    return _build
