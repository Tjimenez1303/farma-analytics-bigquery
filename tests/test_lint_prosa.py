"""Tests for scripts/lint_prosa.sh."""

import re
import shutil

import pytest

MARK = re.compile(r"^(?P<path>.+?):(?P<line>\d+): (?P<cat>[a-z-]+): (?P<frag>.*)$")

EXPECTED_VIOLATIONS = {
    3: "raya",
    4: "raya",
    5: "guion-como-raya",
    6: "punto-y-coma",
    7: "emoji",
    8: "flecha-o-caja",
    9: "flecha-o-caja",
    10: "comillas-curvas",
    12: "title-case",
    14: "negrita-con-dos-puntos",
    15: "resto-de-herramienta",
    16: "resto-de-herramienta",
    17: "muletilla",
    18: "muletilla",
}


@pytest.fixture
def lint(run_script, repo_root):
    """Run the prose linter with the user's PATH (real ripgrep)."""

    def _run(*args, env=None, input=None):
        proc = run_script([repo_root / "scripts" / "lint_prosa.sh", *args], env=env, input=input)
        marks = [
            MARK.match(line).groupdict() for line in proc.stdout.splitlines() if MARK.match(line)
        ]
        return proc, marks

    return _run


def fixture(repo_root, name):
    return repo_root / "tests" / "fixtures" / "prosa" / name


def test_each_category_is_flagged_once(lint, repo_root):
    proc, marks = lint(fixture(repo_root, "violaciones.md"))
    assert proc.returncode == 1
    found = {(int(m["line"]), m["cat"]) for m in marks}
    assert found == set(EXPECTED_VIOLATIONS.items()), proc.stdout
    assert len(marks) == len(EXPECTED_VIOLATIONS), proc.stdout


@pytest.mark.parametrize("name", ["limpio.md", "usos_permitidos.md"])
def test_clean_documents_have_no_marks(lint, repo_root, name):
    proc, marks = lint(fixture(repo_root, name))
    assert marks == [], proc.stdout
    assert proc.returncode == 0


def test_sql_only_checks_comments(lint, repo_root):
    proc, marks = lint(fixture(repo_root, "comentarios.sql"))
    assert [(int(m["line"]), m["cat"]) for m in marks] == [(1, "raya")], proc.stdout


def test_stdin(lint):
    proc, marks = lint("-", input="Primera línea.\nEl cambio entra hoy — sin revisión.\n")
    assert proc.returncode == 1
    assert [(m["path"], int(m["line"]), m["cat"]) for m in marks] == [("<stdin>", 2, "raya")]


def test_new_filler_word_without_touching_script(lint, repo_root, tmp_path):
    custom = tmp_path / "muletillas.txt"
    shutil.copy(repo_root / "scripts" / "muletillas.txt", custom)
    with custom.open("a", encoding="utf-8") as handle:
        handle.write("palabra comodín\n")
    doc = tmp_path / "nota.md"
    doc.write_text("Este texto usa una palabra comodín.\n", encoding="utf-8")

    _, before = lint(doc)
    assert before == []
    env = {"LINT_PROSA_MULETILLAS": str(custom)}
    proc, after = lint(doc, env=env)
    assert [m["cat"] for m in after] == ["muletilla"], proc.stdout


def test_spec_kit_folders_are_excluded(lint, repo_root):
    proc, marks = lint(repo_root / "specs", repo_root / ".specify")
    assert marks == []
    assert proc.returncode == 0


def test_missing_path_is_usage_error(lint, repo_root):
    proc, _ = lint(repo_root / "no-existe.md")
    assert proc.returncode == 2


def test_readme_has_no_marks(lint, repo_root):
    proc, marks = lint(repo_root / "README.md")
    assert marks == [], proc.stdout
