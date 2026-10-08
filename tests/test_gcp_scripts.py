"""Tests for the GCP setup targets and scripts using a fake gcloud and bq."""

import pytest

MAKE = "/usr/bin/make"


@pytest.fixture
def gcp(run_script, stub_path, repo_root, tmp_path):
    """Run a script or make target with stubs and return (process, log lines)."""

    def _run(args, overrides=None, drop=()):
        env = stub_path(
            {
                "PROJECT_ID": "proyecto-demo",
                "BILLING_ACCOUNT_ID": "000000-000000-000000",
                "BUDGET_AMOUNT": "10USD",
                "QUERY_QUOTA_GIB_PER_DAY": "100",
            }
        )
        env.update(overrides or {})
        for key in drop:
            env.pop(key, None)
        proc = run_script(args, env=env)
        log_path = tmp_path / "stub.log"
        lines = log_path.read_text().splitlines() if log_path.exists() else []
        return proc, lines

    return _run


def budget(gcp, repo_root, **kwargs):
    return gcp([repo_root / "scripts" / "gcp_budget.sh"], **kwargs)


def quota(gcp, repo_root, **kwargs):
    return gcp([repo_root / "scripts" / "gcp_quota.sh"], **kwargs)


def test_budget_is_created_when_missing(gcp, repo_root):
    proc, log = budget(gcp, repo_root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    creates = [line for line in log if "billing budgets create" in line]
    assert len(creates) == 1
    cmd = creates[0]
    for part in (
        "--billing-account=000000-000000-000000",
        "--display-name=farma-analytics-bigquery",
        "--budget-amount=10USD",
        "--calendar-period=month",
        "--filter-projects=projects/proyecto-demo",
        "--threshold-rule=percent=0.5",
        "--threshold-rule=percent=0.9",
        "--threshold-rule=percent=1.0",
        "--billing-project=proyecto-demo",
    ):
        assert part in cmd, part
    assert not any("billing budgets update" in line for line in log)


def test_budget_is_updated_when_present(gcp, repo_root):
    name = "billingAccounts/000000-000000-000000/budgets/abc123"
    proc, log = budget(gcp, repo_root, overrides={"STUB_BUDGETS": name})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    updates = [line for line in log if "billing budgets update" in line]
    assert len(updates) == 1
    cmd = updates[0]
    assert name in cmd
    assert "--clear-threshold-rules" in cmd
    for pct in ("0.5", "0.9", "1.0"):
        assert f"--add-threshold-rule=percent={pct}" in cmd
    assert "--threshold-rule=" not in cmd.replace("--add-threshold-rule=", "")
    assert not any("billing budgets create" in line for line in log)


def test_duplicate_budgets_stop(gcp, repo_root):
    proc, log = budget(gcp, repo_root, overrides={"STUB_BUDGETS": "budgets/a,budgets/b"})
    assert proc.returncode == 1
    assert "budgets/a" in proc.stdout + proc.stderr
    assert not any("create" in line or "update" in line for line in log)


@pytest.mark.parametrize("missing", ["BILLING_ACCOUNT_ID", "BUDGET_AMOUNT", "PROJECT_ID"])
def test_budget_requires_variables(gcp, repo_root, missing):
    proc, log = budget(gcp, repo_root, drop=(missing,))
    assert proc.returncode == 1
    assert missing in proc.stdout + proc.stderr
    assert log == []


def test_quota_is_applied_in_mib(gcp, repo_root):
    proc, log = quota(gcp, repo_root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    updates = [line for line in log if "quotas preferences update" in line]
    assert len(updates) == 1
    cmd = updates[0]
    for part in (
        "farma-query-usage-per-day",
        "--service=bigquery.googleapis.com",
        "--quota-id=QueryUsagePerDay",
        "--preferred-value=102400",
        "--project=proyecto-demo",
        "--allow-missing",
        "--allow-high-percentage-quota-decrease",
    ):
        assert part in cmd, part


@pytest.mark.parametrize("value", [None, "abc", "0", "1.5"])
def test_quota_requires_positive_integer(gcp, repo_root, value):
    overrides = {} if value is None else {"QUERY_QUOTA_GIB_PER_DAY": value}
    drop = ("QUERY_QUOTA_GIB_PER_DAY",) if value is None else ()
    proc, log = quota(gcp, repo_root, overrides=overrides, drop=drop)
    assert proc.returncode == 1
    assert log == []


def test_quota_stops_on_unexpected_unit(gcp, repo_root):
    proc, log = quota(gcp, repo_root, overrides={"STUB_QUOTA_UNIT": "TiBy/d/{project}"})
    assert proc.returncode == 1
    assert "TiBy/d/{project}" in proc.stdout + proc.stderr
    assert not any("quotas preferences update" in line for line in log)


def make_dialect(gcp, repo_root, **kwargs):
    return gcp(
        [MAKE, "-C", repo_root, "GOOGLE_CLOUD_PROJECT=proyecto-demo", "gcp-dialect"], **kwargs
    )


def test_dialect_runs_dry_run_first(gcp, repo_root):
    proc, log = make_dialect(gcp, repo_root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    queries = [line for line in log if line.startswith("bq ") and " query " in line]
    assert len(queries) == 2
    assert "--dry_run" in queries[0]
    assert "--dry_run" not in queries[1]
    assert "--label=project:farma-analytics" in queries[1]
    for line in queries:
        assert "region-us.default_sql_dialect_option" in line
        assert "only_google_sql" in line
        assert "--use_legacy_sql" not in line


def test_dialect_stops_when_dry_run_fails(gcp, repo_root):
    proc, log = make_dialect(gcp, repo_root, overrides={"STUB_DRYRUN": "denied"})
    assert proc.returncode != 0
    queries = [line for line in log if line.startswith("bq ") and " query " in line]
    assert len(queries) == 1
    assert "--dry_run" in queries[0]
    assert "BigQuery Admin" in proc.stdout + proc.stderr
