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

EXPECTED_TRUST_POSTURES = {
    "lotus-manage:PortfolioActionRegister:v1": {
        "freshness_state": "current",
        "completeness_status": "complete",
        "reconciliation_status": "reconciled",
        "data_quality_status": "quality_passed",
        "evidence_access_class": "customer_consumable",
        "blocked": False,
        "runtime_certification": "repo_native_contract_fixture",
        "certification_ready": None,
    },
    "lotus-manage:BulkReviewCampaignMembership:v1": {
        "freshness_state": "current",
        "completeness_status": "complete",
        "reconciliation_status": "reconciled",
        "data_quality_status": "quality_passed",
        "evidence_access_class": "customer_consumable",
        "blocked": False,
        "runtime_certification": "repo_native_contract_fixture",
        "certification_ready": None,
    },
    "lotus-manage:PmOperatingQualityScoreRun:v1": {
        "freshness_state": "unknown",
        "completeness_status": "blocked",
        "reconciliation_status": "blocked",
        "data_quality_status": "quality_blocked",
        "evidence_access_class": "operator_only",
        "blocked": True,
        "runtime_certification": "repo_native_contract_fixture_blocked",
        "certification_ready": False,
    },
}

PM_QUALITY_CERTIFICATION_BLOCKERS = {
    "sgajbi/lotus-manage#595",
    "sgajbi/lotus-manage#596",
    "sgajbi/lotus-manage#603",
    "sgajbi/lotus-manage#606",
    "sgajbi/lotus-manage#609",
    "sgajbi/lotus-manage#610",
}


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
    assert set(EXPECTED_TRUST_POSTURES) == expected_product_ids
    assert sorted(path.name for path, _ in snapshots.values()) == sorted(
        _snapshot_filename(product) for product in products
    )

    for product in products:
        product_id = _product_id(product)
        path, telemetry = snapshots[product_id]
        expected_posture = EXPECTED_TRUST_POSTURES[product_id]
        assert telemetry["producer_repository"] == product["owner_repository"]
        assert telemetry["product_name"] == product["product_name"]
        assert telemetry["product_version"] == product["product_version"]
        assert telemetry["serving_routes"] == product["current_routes"]
        assert (
            telemetry["freshness"]["freshness_class"]
            == (product["freshness_policy"]["freshness_class"])
        )
        assert telemetry["freshness"]["freshness_state"] == expected_posture["freshness_state"]
        assert telemetry["completeness_status"] == expected_posture["completeness_status"]
        assert telemetry["reconciliation_status"] == expected_posture["reconciliation_status"]
        assert telemetry["data_quality_status"] == expected_posture["data_quality_status"]
        assert set(telemetry["observed_trust_metadata"]) == set(product["required_trust_metadata"])
        assert (
            telemetry["lineage"]["evidence_access_class"]
            == expected_posture["evidence_access_class"]
        )
        assert telemetry["lineage"]["evidence_uris"] != []
        assert telemetry["blocking"]["blocked"] is expected_posture["blocked"]
        assert (
            telemetry["certification_limits"]["runtime_certification"]
            == expected_posture["runtime_certification"]
        )
        assert (
            telemetry["certification_limits"]["live_environment_certification"]
            == "not_asserted_by_snapshot"
        )
        assert telemetry["evidence"]["validation_lanes"] == ["feature", "pr-merge"]
        assert telemetry["evidence"]["source_artifact_uri"] == (
            f"lotus-manage://contracts/trust-telemetry/{path.name}"
        )
        if expected_posture["certification_ready"] is None:
            assert "certification_ready" not in telemetry["certification_limits"]
            assert "blocked_reason" not in telemetry["blocking"]
        else:
            assert (
                telemetry["certification_limits"]["certification_ready"]
                is expected_posture["certification_ready"]
            )
            assert telemetry["blocking"]["blocked_reason"] == "PM_QUALITY_CERTIFICATION_BLOCKED"
            assert set(telemetry["blocking"]["blocker_issue_refs"]) == (
                PM_QUALITY_CERTIFICATION_BLOCKERS
            )
            assert "quality_passed" not in {
                telemetry["data_quality_status"],
                telemetry["observed_trust_metadata"]["data_quality_status"],
            }
