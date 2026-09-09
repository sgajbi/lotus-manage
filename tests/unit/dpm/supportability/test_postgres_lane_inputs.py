"""The live PostgreSQL lane must execute the complete integration tree (#693).

A hand-written subset cannot prove reachability. Adapter use may arrive through
direct imports, package exports, local helpers or pytest fixtures, and every
classifier for those shapes creates another way for a real proof to disappear.
The database lane therefore owns all integration modules. This contract pins
that simple invariant and makes a future narrowing fail visibly.
"""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MAKEFILE = REPOSITORY_ROOT / "Makefile"
INTEGRATION_ROOT = REPOSITORY_ROOT / "tests" / "integration"


def _lane_paths() -> list[str]:
    """Read POSTGRES_INTEGRATION_TESTS, following Make line continuations."""

    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(
        r"^POSTGRES_INTEGRATION_TESTS\s*=\s*((?:.*\\\n)*.*)$",
        text,
        re.MULTILINE,
    )
    assert match, "the lane variable POSTGRES_INTEGRATION_TESTS is not defined"
    return [
        token
        for token in match.group(1).replace("\\\n", " ").split()
        if token and not token.startswith("$")
    ]


def test_postgres_lane_owns_the_complete_integration_tree() -> None:
    assert _lane_paths() == ["tests/integration"]

    integration_files = sorted(INTEGRATION_ROOT.rglob("test_*.py"))
    assert integration_files, "the integration lane contains no test modules"
    lane_root = (REPOSITORY_ROOT / _lane_paths()[0]).resolve()
    assert all(lane_root in path.resolve().parents for path in integration_files)


def test_postgres_lane_target_uses_the_governed_variable() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    for target in (
        "test-idea-management-action-postgres",
        "test-idea-management-action-postgres-coverage",
    ):
        match = re.search(rf"^{target}:\n((?:\t.*\n)+)", text, re.MULTILINE)
        assert match, f"Makefile target {target} is missing"
        assert "$(POSTGRES_INTEGRATION_TESTS)" in match.group(1)
