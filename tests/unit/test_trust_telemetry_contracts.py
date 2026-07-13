from __future__ import annotations

import json
import re
import shutil
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
IDEA_ACTION_INTAKE_CONTRACT_PATH = (
    ROOT / "contracts" / "idea-action-intake" / "lotus-manage-idea-action-intake.v1.json"
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


def test_repo_native_trust_telemetry_validation_rejects_certified_route_foundation_leak(
    tmp_path: Path,
) -> None:
    if not platform_validation_dependencies_available():
        pytest.skip("sibling lotus-platform trust telemetry validator is not available")

    telemetry_dir = tmp_path / "trust-telemetry"
    telemetry_dir.mkdir()
    for source_path in LOCAL_TELEMETRY_DIR.glob("*.json"):
        shutil.copy2(source_path, telemetry_dir / source_path.name)

    product_declaration_path = tmp_path / "lotus-manage-products.v1.json"
    shutil.copy2(PRODUCT_DECLARATION_PATH, product_declaration_path)
    portfolio_snapshot_path = telemetry_dir / "portfolio-action-register.telemetry.v1.json"
    portfolio_snapshot = json.loads(portfolio_snapshot_path.read_text(encoding="utf-8"))
    portfolio_snapshot["serving_routes"].append("/api/v1/rebalance/idea-action-intake")
    portfolio_snapshot_path.write_text(json.dumps(portfolio_snapshot), encoding="utf-8")

    issues = validate_repo_native_trust_telemetry(
        telemetry_dir,
        product_declaration_path=product_declaration_path,
    )

    assert any(
        "not-certified route foundation /api/v1/rebalance/idea-action-intake "
        "must not be listed in serving_routes"
        in issue
        for issue in issues
    )


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
    assert telemetry["serving_routes"] == product["current_routes"]
    assert telemetry["route_foundations"] == product["route_foundations"]
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
        assert telemetry.get("route_foundations", []) == product.get("route_foundations", [])
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


def test_not_certified_route_foundations_do_not_inherit_unblocked_serving_route_posture() -> None:
    products = _load_product_declaration()["products"]
    snapshots = _load_telemetry_snapshots_by_product_id()
    idea_intake_contract = json.loads(IDEA_ACTION_INTAKE_CONTRACT_PATH.read_text(encoding="utf-8"))

    for product in products:
        product_id = _product_id(product)
        _, telemetry = snapshots[product_id]
        certified_routes = set(product.get("current_routes", []))
        telemetry_serving_routes = set(telemetry["serving_routes"])
        assert telemetry_serving_routes == certified_routes

        for route_foundation in product.get("route_foundations", []):
            route = route_foundation["route"].removeprefix("POST ")
            has_blockers = bool(route_foundation.get("certification_blockers"))
            is_not_certified = route_foundation.get("supportability_status") == "not_certified"
            is_not_promoted = route_foundation.get("supported_feature_promoted") is False
            if is_not_certified or is_not_promoted or has_blockers:
                assert route not in certified_routes
                assert route not in telemetry_serving_routes
                assert route_foundation in telemetry.get("route_foundations", [])

    portfolio_snapshot = snapshots["lotus-manage:PortfolioActionRegister:v1"][1]
    [foundation] = portfolio_snapshot["route_foundations"]
    assert foundation["route"] == idea_intake_contract["target_route"]
    assert foundation["supportability_status"] == idea_intake_contract["supportability_status"]
    assert (
        foundation["supported_feature_promoted"]
        is idea_intake_contract["supported_feature_promoted"]
    )
    assert foundation["certification_blockers"] == idea_intake_contract["certification_blockers"]
