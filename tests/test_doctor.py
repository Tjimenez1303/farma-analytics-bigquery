"""Tests for scripts/doctor.sh using fake gcloud, bq and friends."""

import json
import re

import pytest

LINE = re.compile(r"^(OK|AVISO|FALLO|OMITIDO)\s+([A-Z]\d\d)\s")


def parse(stdout):
    """Map check id to (status, remedy) from the doctor report."""
    result = {}
    last = None
    for line in stdout.splitlines():
        match = LINE.match(line)
        if match:
            last = match.group(2)
            result[last] = [match.group(1), ""]
        elif last and line.strip().startswith("remedio:"):
            result[last][1] = line.strip()
    return result


@pytest.fixture
def doctor(run_script, stub_path, repo_root, tmp_path):
    """Run the doctor with a healthy fake environment plus overrides."""

    home = tmp_path / "home"
    adc_dir = home / ".config" / "gcloud"
    adc_dir.mkdir(parents=True)
    (adc_dir / "application_default_credentials.json").write_text(
        json.dumps({"type": "authorized_user", "quota_project_id": "proyecto-demo"})
    )

    def _run(overrides=None, remove=(), drop=()):
        env = stub_path(
            {
                "HOME": str(home),
                "BIGQUERYRC": str(repo_root / ".bigqueryrc"),
                "DOCTOR_TIMEOUT": "5",
                "STUB_ACCOUNT": "persona@example.com",
                "STUB_ADC": "ok",
                "STUB_PROJECT": "proyecto-demo",
                "STUB_BILLING": "True",
                "STUB_DRYRUN": "ok",
                "STUB_DRYRUN_LOCATION": "US",
                "STUB_LEGACY": "rejected",
                "STUB_DATASET_LOCATION": "",
                "STUB_NETWORK": "ok",
            },
            remove=remove,
        )
        env.update(overrides or {})
        for key in drop:
            env.pop(key, None)
        proc = run_script([repo_root / "scripts" / "doctor.sh"], env=env)
        log_path = tmp_path / "stub.log"
        log = log_path.read_text() if log_path.exists() else ""
        return proc, parse(proc.stdout), log

    return _run


def test_healthy_environment(doctor):
    proc, checks, _ = doctor()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert checks["B03"][0] == "OMITIDO"
    others = {k: v[0] for k, v in checks.items() if k != "B03"}
    assert set(others.values()) == {"OK"}, others
    assert len(checks) == 24
    assert "Resumen:" in proc.stdout


@pytest.mark.parametrize(
    "check, kwargs",
    [
        ("T08", {"remove": ("rg",)}),
        ("T04", {"overrides": {"STUB_NODE_VERSION": "20.11.0"}}),
        ("T03", {"overrides": {"STUB_PYTHON_VERSION": "3.11.9"}}),
        ("A02", {"overrides": {"STUB_ADC": "missing"}}),
        ("P01", {"overrides": {"STUB_PROJECT": ""}}),
        ("B02", {"overrides": {"STUB_LEGACY": "accepted"}}),
        ("B03", {"overrides": {"STUB_DATASET_LOCATION": "EU"}}),
        ("C03", {"overrides": {"GOOGLE_APPLICATION_CREDENTIALS": "__REPO__/clave.json"}}),
    ],
)
def test_induced_failures(doctor, repo_root, check, kwargs):
    overrides = {
        k: v.replace("__REPO__", str(repo_root)) for k, v in kwargs.get("overrides", {}).items()
    }
    proc, checks, _ = doctor(overrides=overrides, remove=kwargs.get("remove", ()))
    assert proc.returncode == 1, proc.stdout
    assert checks[check][0] == "FALLO", proc.stdout
    assert checks[check][1].startswith("remedio:"), proc.stdout


def test_dialect_remedy_names_region(doctor):
    _, checks, _ = doctor(overrides={"STUB_LEGACY": "accepted"})
    assert "make gcp-dialect" in checks["B02"][1]
    assert "region-us" in checks["B02"][1]


def test_missing_bigqueryrc_exits_2(doctor):
    proc, _, _ = doctor(drop=("BIGQUERYRC",))
    assert proc.returncode == 2


def test_missing_project_skips_bigquery_checks(doctor):
    _, checks, _ = doctor(overrides={"STUB_PROJECT": ""})
    for check in ("P02", "B01", "B02", "B03"):
        assert checks[check][0] == "OMITIDO", check


def test_uv_failure_cascades(doctor):
    _, checks, _ = doctor(overrides={"STUB_UV_VERSION": "0.11.0"})
    assert checks["T10"][0] == "FALLO"
    for check in ("T03", "T06", "T07"):
        assert checks[check][0] == "OMITIDO", check


def test_no_network_skips_remote_checks(doctor):
    proc, checks, _ = doctor(overrides={"STUB_NETWORK": "down"})
    assert checks["N01"][0] == "OMITIDO"
    for check in ("A01", "A02", "A03", "A04", "P02", "B01", "B02", "B03"):
        assert checks[check][0] == "OMITIDO", check
    assert checks["P01"][0] == "OK"
    assert proc.returncode == 0


def test_project_mismatch_is_warning(doctor):
    proc, checks, _ = doctor(overrides={"GOOGLE_CLOUD_PROJECT": "otro-proyecto"})
    assert checks["P01"][0] == "AVISO"
    assert proc.returncode == 0


def test_personal_bigqueryrc_is_warning(doctor, tmp_path):
    (tmp_path / "home" / ".bigqueryrc").write_text("--location=EU\n")
    _, checks, _ = doctor()
    assert checks["C02"][0] == "AVISO"


def test_every_bq_query_is_a_dry_run(doctor):
    _, _, log = doctor()
    queries = [line for line in log.splitlines() if line.startswith("bq ") and " query " in line]
    assert queries, "the doctor should run at least one dry run"
    assert all("--dry_run" in line for line in queries), queries


def test_token_is_never_printed(doctor):
    proc, _, log = doctor()
    assert "fake-token" not in proc.stdout + proc.stderr
    assert "fake-token" not in log


def test_bq_errors_on_stdout_are_recognized(doctor):
    _, checks, _ = doctor(overrides={"STUB_ERRORS_ON_STDOUT": "1", "STUB_DRYRUN": "ok"})
    assert checks["B03"][0] == "OMITIDO"
    assert checks["B02"][0] == "OK"


def test_missing_dataset_reason(doctor):
    proc, _, _ = doctor(overrides={"STUB_ERRORS_ON_STDOUT": "1"})
    assert "el dataset aún no existe" in proc.stdout


def test_disabled_api_on_stdout(doctor):
    _, checks, _ = doctor(overrides={"STUB_ERRORS_ON_STDOUT": "1", "STUB_DRYRUN": "disabled"})
    assert checks["B01"][0] == "FALLO"
    assert "services enable" in checks["B01"][1]
