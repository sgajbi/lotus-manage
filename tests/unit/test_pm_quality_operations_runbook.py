from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pm_quality_operations_runbook_covers_triage_states_and_replay() -> None:
    runbook = (ROOT / "wiki" / "Operations-Runbook.md").read_text(encoding="utf-8")

    required_terms = [
        "## PM-quality lifecycle operations",
        "lotus_manage_pm_quality_lifecycle_total",
        "Problem Details `reasonCode`",
        "`DISABLED`",
        "`BLOCKED`",
        "`DEGRADED`",
        "`PENDING_REVIEW`",
        "`READY`",
        "`REQUESTED`",
        "`COMPLETED`",
        "`FAILED`",
        "Preview routes are retry-safe",
        "Create routes are immutable",
        "DPM_CORE_PM_BOOK_MEMBERSHIP_",
        "POSTGRES_CONNECTION_ACQUIRE_TIMEOUT",
        "generated summary text",
        "python scripts/validate_observability_contracts.py",
        "tests/integration/dpm/pm_quality/test_pm_quality_endpoint_lifecycle.py",
    ]

    missing = [term for term in required_terms if term not in runbook]
    assert missing == []


def test_operations_runbook_links_pm_quality_support_path() -> None:
    docs_runbook = (ROOT / "docs" / "operations-runbook.md").read_text(encoding="utf-8")

    assert "wiki/Operations-Runbook.md#pm-quality-lifecycle-operations" in docs_runbook
    assert "lotus_manage_pm_quality_lifecycle_total" in docs_runbook
    assert "generated summary text" in docs_runbook
