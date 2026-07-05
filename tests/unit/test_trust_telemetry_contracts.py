from __future__ import annotations

import json
import re
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


def _product_id(product: dict) -> str:
    return f"lotus-manage:{product['product_name']}:{product['product_version']}"


def _snapshot_filename(product: dict) -> str:
    product_slug = re.sub(r"(?<!^)(?=[A-Z])", "-", product["product_name"]).lower()
    return f"{product_slug}.telemetry.v1.json"


def _load_product_declaration() -> dict:
    return json.loads(PRODUCT_DECLARATION_PATH.read_text(encoding="utf-8"))


def _load_telemetry_snapshot() -> dict:
    return json.loads(TELEMETRY_PATH.read_text(encoding="utf-8"))


def _load_telemetry_snapshots_by_product_id() -> dict[str, tuple[Path, dict]]:
    snapshots: dict[str, tuple[Path, dict]] = {}
    for path in sorted(LOCAL_TELEMETRY_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshots[payload["product_id"]] = (path, payload)
    return snapshots


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


def test_trust_telemetry_covers_every_active_product_declaration() -> None:
    products = [
        product
        for product in _load_product_declaration()["products"]
        if product["lifecycle_status"] == "active"
    ]
    snapshots = _load_telemetry_snapshots_by_product_id()
    expected_product_ids = {_product_id(product) for product in products}

    assert set(snapshots) == expected_product_ids
    assert sorted(path.name for path, _ in snapshots.values()) == sorted(
        _snapshot_filename(product) for product in products
    )

    for product in products:
        path, telemetry = snapshots[_product_id(product)]
        assert telemetry["producer_repository"] == product["owner_repository"]
        assert telemetry["product_name"] == product["product_name"]
        assert telemetry["product_version"] == product["product_version"]
        assert telemetry["serving_routes"] == product["current_routes"]
        assert (
            telemetry["freshness"]["freshness_class"]
            == (product["freshness_policy"]["freshness_class"])
        )
        assert (
            telemetry["completeness_status"] == (product["completeness_policy"]["default_status"])
        )
        assert telemetry["reconciliation_status"] == "reconciled"
        assert telemetry["data_quality_status"] == "quality_passed"
        assert set(telemetry["observed_trust_metadata"]) == set(product["required_trust_metadata"])
        assert (
            telemetry["lineage"]["evidence_access_class"]
            == (product["lineage_policy"]["evidence_access_class_ref"])
        )
        assert telemetry["lineage"]["evidence_uris"] != []
        assert telemetry["blocking"]["blocked"] is False
        assert telemetry["certification_limits"] == {
            "runtime_certification": "repo_native_contract_fixture",
            "live_environment_certification": "not_asserted_by_snapshot",
            "promotion_limit": "validated by feature and pr-merge lanes only",
        }
        assert telemetry["evidence"]["validation_lanes"] == ["feature", "pr-merge"]
        assert telemetry["evidence"]["source_artifact_uri"] == (
            f"lotus-manage://contracts/trust-telemetry/{path.name}"
        )
