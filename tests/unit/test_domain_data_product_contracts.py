from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_domain_data_product_contracts import (
    LOCAL_DECLARATION_DIR,
    platform_validation_dependencies_available,
    validate_repo_native_contracts,
)


ROOT = Path(__file__).resolve().parents[2]
CONSUMER_DECLARATION_PATH = (
    ROOT / "contracts" / "domain-data-products" / "lotus-manage-consumers.v1.json"
)
PRODUCT_DECLARATION_PATH = (
    ROOT / "contracts" / "domain-data-products" / "lotus-manage-products.v1.json"
)
REQUEST_MODELS_PATH = ROOT / "src" / "api" / "request_models.py"
UPSTREAM_FAMILY_MAP_PATH = ROOT / "docs" / "standards" / "RFC-0082-upstream-contract-family-map.md"
DECLARATION_README_PATH = ROOT / "contracts" / "domain-data-products" / "README.md"


def _load_consumer_declaration() -> dict:
    return json.loads(CONSUMER_DECLARATION_PATH.read_text(encoding="utf-8"))


def _load_product_declaration() -> dict:
    return json.loads(PRODUCT_DECLARATION_PATH.read_text(encoding="utf-8"))


def test_repo_native_domain_data_product_validation_passes_when_platform_is_available() -> None:
    if not platform_validation_dependencies_available(LOCAL_DECLARATION_DIR):
        pytest.skip("sibling lotus-platform contract validator is not available")

    assert validate_repo_native_contracts() == []


def test_manage_consumer_declaration_tracks_current_core_inputs() -> None:
    payload = _load_consumer_declaration()
    dependencies = payload["dependencies"]
    by_name = {dependency["product_name"]: dependency for dependency in dependencies}

    assert payload["consumer_repository"] == "lotus-manage"
    assert set(by_name) == {
        "PortfolioStateSnapshot",
        "ClientRestrictionProfile",
        "SustainabilityPreferenceProfile",
    }
    assert (
        by_name["PortfolioStateSnapshot"]["consumption_mode"] == "caller_supplied_contract_payload"
    )
    assert by_name["PortfolioStateSnapshot"]["failure_posture"] == "fail_closed"
    assert by_name["ClientRestrictionProfile"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["ClientRestrictionProfile"]["failure_posture"] == "degrade_or_block"
    assert (
        by_name["SustainabilityPreferenceProfile"]["consumption_mode"] == "stateful_core_sourcing"
    )
    assert (
        by_name["SustainabilityPreferenceProfile"]["failure_posture"] == "degrade_or_pending_review"
    )

    request_models = REQUEST_MODELS_PATH.read_text(encoding="utf-8")
    assert "portfolio_snapshot: PortfolioSnapshot" in request_models


def test_manage_declaration_limits_live_source_data_api_reads_to_approved_profiles() -> None:
    payload = _load_consumer_declaration()
    dependencies = payload["dependencies"]
    live_dependencies = {
        dependency["product_name"]
        for dependency in dependencies
        if dependency["consumption_mode"] == "stateful_core_sourcing"
    }
    upstream_family_map = UPSTREAM_FAMILY_MAP_PATH.read_text(encoding="utf-8")

    assert live_dependencies == {"ClientRestrictionProfile", "SustainabilityPreferenceProfile"}
    assert "modeled, feature-gated outbound resolver seam" in upstream_family_map
    assert (
        "RFC-087 rebaselines that seam to composed DPM source-data products" in upstream_family_map
    )
    assert "does not declare a promoted live" in upstream_family_map
    assert "execution-context product API-read dependency" in upstream_family_map


def test_manage_declaration_keeps_unapproved_market_data_on_the_watchlist() -> None:
    dependencies = _load_consumer_declaration()["dependencies"]
    product_names = {dependency["product_name"] for dependency in dependencies}
    readme = DECLARATION_README_PATH.read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.split())

    assert "MarketDataWindow" not in product_names
    assert "`MarketDataWindow`" in readme
    assert "not currently approved for `lotus-manage`" in normalized_readme


def test_manage_declaration_directory_contains_consumer_and_owned_product_contracts() -> None:
    declaration_paths = sorted(path.name for path in LOCAL_DECLARATION_DIR.glob("*.json"))

    assert declaration_paths == [
        "lotus-manage-consumers.v1.json",
        "lotus-manage-products.v1.json",
    ]


def test_manage_product_declaration_publishes_portfolio_action_register() -> None:
    payload = _load_product_declaration()
    products = payload["products"]

    assert payload["producer_repository"] == "lotus-manage"
    assert [product["product_name"] for product in products] == ["PortfolioActionRegister"]

    product = products[0]
    assert product["product_version"] == "v1"
    assert product["lifecycle_status"] == "active"
    assert product["approved_consumers"] == ["lotus-gateway"]
    assert product["serving_plane"] == "query_control_plane_service"
    assert product["current_routes"] == [
        "/api/v1/rebalance/supportability/summary",
        "/api/v1/rebalance/runs/{rebalance_run_id}/artifact",
        "/api/v1/rebalance/runs/{rebalance_run_id}/workflow",
        "/api/v1/rebalance/workflow/decisions",
    ]
    assert product["lineage_policy"]["lineage_required"] is True
    assert product["lineage_policy"]["lineage_bundle_class_ref"] == "customer_lineage_summary"


def test_manage_consumer_declaration_keeps_stateful_core_context_on_watchlist() -> None:
    payload = _load_consumer_declaration()
    dependency_names = {dependency["product_name"] for dependency in payload["dependencies"]}
    readme = DECLARATION_README_PATH.read_text(encoding="utf-8")

    assert "DpmExecutionContext" not in dependency_names
    assert "DpmCoreExecutionContext" not in dependency_names
    assert "New core products should be added here only after source-owner approval" in readme
