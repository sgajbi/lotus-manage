"""Durable operator-documentation contract for the quarantine inventory (#699)."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_operator_surfaces_publish_one_safe_quarantine_inventory_command() -> None:
    surfaces = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md",
            "docs/operations-runbook.md",
            "scripts/README.md",
            "REPOSITORY-ENGINEERING-CONTEXT.md",
            "wiki/Operations-Runbook.md",
        )
    }

    assert all("make quarantine-inventory" in content for content in surfaces.values())
    assert "quarantine-inventory:" in (ROOT / "Makefile").read_text(encoding="utf-8")
    runbook = surfaces["docs/operations-runbook.md"]
    for required_truth in (
        "all seven governed datasets",
        "repeatable-read, read-only transaction",
        "explicit successful zero",
        "QUARANTINE_INVENTORY_FAILED",
        "must not be assigned, updated, deleted, or exposed\nthrough an API",
        "Migration `0029` adds the partial index",
    ):
        assert required_truth in runbook
