from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_trust_telemetry_contracts import (
    LOCAL_TELEMETRY_DIR,
    platform_validation_dependencies_available,
    validate_repo_native_trust_telemetry,
)


ROOT = Path(__file__).resolve().parents[2]
PRODUCT_DECLARATION_PATH = (
    ROOT / "contracts" / "domain-data-products" / "lotus-manage-products.v1.json"
)
TELEMETRY_PATH = (
    ROOT / "contracts" / "trust-telemetry" / "portfolio-action-register.telemetry.v1.json"
)


def _load_product_declaration() -> dict:
    return json.loads(PRODUCT_DECLARATION_PATH.read_text(encoding="utf-8"))


def _load_telemetry_snapshot() -> dict:
    return json.loads(TELEMETRY_PATH.read_text(encoding="utf-8"))


def test_repo_native_trust_telemetry_validation_passes_when_platform_is_available() -> None:
    if not platform_validation_dependencies_available():
        pytest.skip("sibling lotus-platform trust telemetry validator is not available")

    assert validate_repo_native_trust_telemetry() == []


def test_trust_telemetry_snapshot_matches_portfolio_action_register_declaration() -> None:
    product = _load_product_declaration()["products"][0]
    telemetry = _load_telemetry_snapshot()

    assert telemetry["product_id"] == "lotus-manage:PortfolioActionRegister:v1"
    assert telemetry["producer_repository"] == product["owner_repository"]
    assert telemetry["product_name"] == product["product_name"]
    assert telemetry["product_version"] == product["product_version"]
    assert set(telemetry["observed_trust_metadata"]) == set(product["required_trust_metadata"])
    assert (
        telemetry["lineage"]["evidence_access_class"]
        == product["lineage_policy"]["evidence_access_class_ref"]
    )
    assert telemetry["evidence"]["validation_lanes"] == ["feature", "pr-merge"]


def test_trust_telemetry_directory_contains_only_repo_native_snapshots() -> None:
    assert sorted(path.name for path in LOCAL_TELEMETRY_DIR.glob("*.json")) == [
        "portfolio-action-register.telemetry.v1.json"
    ]
